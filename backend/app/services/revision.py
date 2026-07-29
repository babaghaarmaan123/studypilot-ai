"""Spaced repetition.

When a topic is completed we book four recall checkpoints:

    +2 days   first consolidation
    +7 days   short-term retention
    +14 days  long-term retention
    -3 days from the exam   final pass

A weak recall rating pulls the next checkpoint closer; a strong one pushes it
out, so the schedule adapts to how well the student is actually remembering.
"""

from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RevisionPlan, Subject, Topic, User

INTERVALS: List[tuple[str, int, int]] = [
    # (label, days after completion, minutes)
    ("2d", 2, 25),
    ("7d", 7, 30),
    ("14d", 14, 35),
]

FINAL_REVISION_LEAD_DAYS = 3


def _next_exam_date(subject: Subject, after: date) -> Optional[date]:
    upcoming = [e.exam_date for e in subject.exams if e.exam_date >= after]
    return min(upcoming) if upcoming else None


def schedule_for_topic(
    db: Session,
    user: User,
    topic: Topic,
    subject: Subject,
    completed_on: Optional[date] = None,
) -> List[RevisionPlan]:
    """Create the spaced-repetition ladder for a freshly completed topic."""
    start = completed_on or date.today()

    # Clear any pending entries from a previous completion of the same topic.
    existing = db.scalars(
        select(RevisionPlan).where(
            RevisionPlan.topic_id == topic.id,
            RevisionPlan.user_id == user.id,
            RevisionPlan.status == "pending",
        )
    ).all()
    for entry in existing:
        db.delete(entry)

    exam_date = _next_exam_date(subject, start)
    created: List[RevisionPlan] = []

    for index, (label, offset, minutes) in enumerate(INTERVALS, start=1):
        scheduled = start + timedelta(days=offset)
        if exam_date and scheduled >= exam_date:
            break
        created.append(
            RevisionPlan(
                user_id=user.id,
                topic_id=topic.id,
                subject_id=subject.id,
                scheduled_date=scheduled,
                interval_label=label,
                repetition_index=index,
                duration_minutes=minutes,
            )
        )

    if exam_date:
        final_day = exam_date - timedelta(days=FINAL_REVISION_LEAD_DAYS)
        if final_day > start:
            created.append(
                RevisionPlan(
                    user_id=user.id,
                    topic_id=topic.id,
                    subject_id=subject.id,
                    scheduled_date=final_day,
                    interval_label="final",
                    repetition_index=len(created) + 1,
                    duration_minutes=40,
                )
            )

    for entry in created:
        db.add(entry)
    db.flush()
    return created


def complete_revision(
    db: Session, user: User, revision: RevisionPlan, recall_rating: int
) -> Optional[RevisionPlan]:
    """Mark a revision done and, if recall was poor, book an earlier retry."""
    from app.db.base import utcnow

    revision.status = "completed"
    revision.recall_rating = recall_rating
    revision.completed_at = utcnow()
    db.add(revision)

    follow_up: Optional[RevisionPlan] = None
    if recall_rating <= 2:
        # Struggled — see it again in two days.
        follow_up = RevisionPlan(
            user_id=user.id,
            topic_id=revision.topic_id,
            subject_id=revision.subject_id,
            scheduled_date=date.today() + timedelta(days=2),
            interval_label="retry",
            repetition_index=revision.repetition_index + 1,
            duration_minutes=max(25, revision.duration_minutes),
        )
        db.add(follow_up)
        # Recall was weak, so the topic is no longer "done".
        if revision.topic and revision.topic.status == "completed":
            revision.topic.status = "in_progress"
            db.add(revision.topic)

    db.flush()
    return follow_up


def due_revisions(
    db: Session, user: User, on: Optional[date] = None
) -> List[RevisionPlan]:
    today = on or date.today()
    return list(
        db.scalars(
            select(RevisionPlan)
            .where(
                RevisionPlan.user_id == user.id,
                RevisionPlan.status == "pending",
                RevisionPlan.scheduled_date <= today,
            )
            .order_by(RevisionPlan.scheduled_date)
        ).all()
    )


def upcoming_revisions(
    db: Session, user: User, days: int = 30
) -> List[RevisionPlan]:
    today = date.today()
    return list(
        db.scalars(
            select(RevisionPlan)
            .where(
                RevisionPlan.user_id == user.id,
                RevisionPlan.scheduled_date <= today + timedelta(days=days),
            )
            .order_by(RevisionPlan.scheduled_date)
        ).all()
    )


def revision_stats(db: Session, user: User) -> dict:
    entries = db.scalars(
        select(RevisionPlan).where(RevisionPlan.user_id == user.id)
    ).all()
    total = len(entries)
    if not total:
        return {"total": 0, "completed": 0, "pending": 0, "missed": 0, "rate": 0.0}

    completed = sum(1 for e in entries if e.status == "completed")
    missed = sum(1 for e in entries if e.status == "missed")
    return {
        "total": float(total),
        "completed": float(completed),
        "pending": float(total - completed - missed),
        "missed": float(missed),
        "rate": round(completed / total * 100, 1),
    }
