"""Subject creation, syllabus seeding and deletion."""

from typing import Iterable, List, Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.data import syllabus as syllabus_data
from app.data.catalog import colour_for_subject
from app.models import StudySession, Subject, Topic, Unit, User


def delete_subject(db: Session, subject: Subject) -> None:
    """Remove a subject and everything hanging off it.

    Units, topics, completions, revisions, exams and past papers all go via
    relationship cascades. Timetabled sessions do not: `StudySession` points at
    a subject with a database-level `ON DELETE CASCADE` but has no ORM
    relationship back from `Subject`, so SQLAlchemy would leave the rows for the
    database to deal with — and their `subject_id` would still be loaded in this
    session's identity map. Clearing them here makes the delete behave the same
    whichever engine is underneath.
    """
    db.execute(delete(StudySession).where(StudySession.subject_id == subject.id))
    db.delete(subject)


def delete_subjects(db: Session, subjects: Iterable[Subject]) -> List[str]:
    """Delete several subjects, returning their names for logging."""
    removed: List[str] = []
    for subject in list(subjects):
        removed.append(subject.name)
        delete_subject(db, subject)
    if removed:
        db.flush()
    return removed


def _forget_deleted_subjects(db: Session, user: User) -> None:
    """Drop the loaded `user.subjects` collection after deleting from it.

    The session keeps returning the deleted instances otherwise, and touching
    one raises `InvalidRequestError` — which is exactly what happens next, when
    the mentor summary walks the student's subjects to describe them.
    """
    db.expire(user, ["subjects"])


def prune_for_curriculum(db: Session, user: User, curriculum: Optional[str]) -> List[str]:
    """Delete the student's subjects that belong to a different curriculum.

    A subject with no curriculum recorded is treated as belonging to whatever
    the student was studying before, so switching course clears it too.
    """
    if not curriculum:
        return []
    stale = [
        subject
        for subject in user.subjects
        if (subject.curriculum or curriculum) != curriculum
    ]
    removed = delete_subjects(db, stale)
    if removed:
        _forget_deleted_subjects(db, user)
    return removed


def prune_missing(db: Session, user: User, keep_names: Iterable[str]) -> List[str]:
    """Delete any subject whose name is not in `keep_names`.

    Used when onboarding is re-run: the answers submitted at question 4 are the
    full list of subjects the student is studying, so anything absent from it
    has been dropped.
    """
    wanted = {name.strip().lower() for name in keep_names if name and name.strip()}
    if not wanted:
        # Never interpret "no answer" as "delete everything".
        return []
    stale = [s for s in user.subjects if s.name.strip().lower() not in wanted]
    removed = delete_subjects(db, stale)
    if removed:
        _forget_deleted_subjects(db, user)
    return removed


def seed_syllabus(db: Session, subject: Subject) -> int:
    """Populate a subject with its template units and topics.

    Returns the number of topics created. Safe to call only on an empty
    subject — callers check first.
    """
    template = syllabus_data.template_for(subject.name, subject.curriculum)
    created = 0
    for unit_index, (unit_name, topics) in enumerate(template.items()):
        unit = Unit(subject=subject, name=unit_name, order_index=unit_index)
        db.add(unit)
        for topic_index, (topic_name, hours, difficulty) in enumerate(topics):
            db.add(
                Topic(
                    unit=unit,
                    name=topic_name,
                    estimated_hours=hours,
                    difficulty=difficulty,
                    order_index=topic_index,
                )
            )
            created += 1
    return created


def create_subject(
    db: Session,
    user: User,
    name: str,
    *,
    curriculum: Optional[str] = None,
    exam_board: Optional[str] = None,
    colour: Optional[str] = None,
    difficulty: Optional[int] = None,
    priority: str = "medium",
    estimated_hours: Optional[float] = None,
    target_grade: Optional[str] = None,
    confidence: int = 3,
    index_hint: int = 0,
    seed: bool = False,
) -> Subject:
    """Create a subject, defaulting anything the student did not specify from
    the syllabus template (hours, difficulty) and the palette (colour)."""
    resolved_curriculum = curriculum or user.curriculum

    subject = Subject(
        user_id=user.id,
        name=name.strip(),
        curriculum=resolved_curriculum,
        exam_board=exam_board,
        colour=colour or colour_for_subject(name, index_hint),
        difficulty=difficulty
        or syllabus_data.average_difficulty_for(name, resolved_curriculum),
        priority=priority,
        estimated_hours=estimated_hours
        or syllabus_data.estimated_hours_for(name, resolved_curriculum),
        target_grade=target_grade,
        confidence=confidence,
        is_weak=confidence <= 2,
    )
    db.add(subject)
    db.flush()

    if seed:
        seed_syllabus(db, subject)
        db.flush()

    return subject


def apply_parsed_units(
    db: Session,
    subject: Subject,
    units: list,
) -> int:
    """Replaces a subject's syllabus with freshly parsed units/topics.

    `units` is the
    `[(unit_name, [(topic_name, hours, difficulty, key_points), ...]), ...]`
    shape produced by `services.syllabus_parser.parse_pdf`, where `key_points`
    is the newline-separated list of content statements the board sets for that
    topic (and may be omitted). Any existing units are deleted first (cascades
    to topics) so re-uploading a PDF cleanly replaces the old breakdown.
    Returns the number of topics created.
    """
    for unit in list(subject.units):
        db.delete(unit)
    db.flush()

    created = 0
    for unit_index, (unit_name, topics) in enumerate(units):
        unit = Unit(subject=subject, name=unit_name, order_index=unit_index)
        db.add(unit)
        for topic_index, entry in enumerate(topics):
            topic_name, hours, difficulty = entry[0], entry[1], entry[2]
            key_points = entry[3] if len(entry) > 3 else None
            db.add(
                Topic(
                    unit=unit,
                    name=topic_name,
                    estimated_hours=hours,
                    difficulty=difficulty,
                    order_index=topic_index,
                    notes=key_points,
                )
            )
            created += 1
    return created


def recalculate_weak_subjects(db: Session, user: User) -> None:
    """Flag subjects that are behind, hard, or self-rated low confidence.

    A subject is "weak" when at least two of these hold:
      * completion is under 40%
      * difficulty is 4 or 5
      * self-rated confidence is 2 or below
      * average past-paper score is under 60%
    """
    for subject in user.subjects:
        if subject.is_archived:
            continue

        signals = 0
        if subject.completion_percentage < 40:
            signals += 1
        if subject.difficulty >= 4:
            signals += 1
        if subject.confidence <= 2:
            signals += 1

        papers = [p for p in subject.past_papers if p.scored]
        if papers:
            average = sum(p.percentage for p in papers) / len(papers)
            if average < 60:
                signals += 1

        subject.is_weak = signals >= 2
        db.add(subject)
