"""Subject creation and syllabus seeding."""

from typing import Optional

from sqlalchemy.orm import Session

from app.data import syllabus as syllabus_data
from app.data.catalog import colour_for_subject
from app.models import Subject, Topic, Unit, User


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
