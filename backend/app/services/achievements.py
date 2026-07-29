"""Achievement definitions and evaluation.

Each definition knows how to measure itself from the database, so unlocking is
a single pass over the catalogue rather than sprinkled through the endpoints.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import (
    Achievement,
    CompletedTopic,
    PastPaper,
    StudySession,
    Subject,
    User,
)
from app.services.activity import award_xp, log_activity, notify


@dataclass(frozen=True)
class Definition:
    code: str
    name: str
    description: str
    icon: str
    tier: str
    xp: int
    target: float
    measure: Callable[[Session, User], float]


# --- Measurement helpers ----------------------------------------------------
def _streak(_: Session, user: User) -> float:
    return float(user.streak_current)


def _topics_completed(db: Session, user: User) -> float:
    return float(
        db.scalar(
            select(func.count(CompletedTopic.id)).where(
                CompletedTopic.user_id == user.id
            )
        )
        or 0
    )


def _subjects_finished(_: Session, user: User) -> float:
    return float(
        sum(
            1
            for subject in user.subjects
            if subject.topics and subject.completion_percentage >= 100
        )
    )


def _sessions_completed(db: Session, user: User) -> float:
    return float(
        db.scalar(
            select(func.count(StudySession.id)).where(
                StudySession.user_id == user.id,
                StudySession.status == "completed",
            )
        )
        or 0
    )


def _hours_studied(db: Session, user: User) -> float:
    minutes = (
        db.scalar(
            select(func.coalesce(func.sum(StudySession.actual_minutes), 0)).where(
                StudySession.user_id == user.id,
                StudySession.status == "completed",
            )
        )
        or 0
    )
    return round(minutes / 60, 1)


def _perfect_week(db: Session, user: User) -> float:
    """1.0 when every session in the last completed 7 days was done."""
    today = date.today()
    start = today - timedelta(days=7)
    rows = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.session_date >= start,
            StudySession.session_date < today,
        )
    ).all()
    if len(rows) < 5:
        return 0.0
    return 1.0 if all(r.status in {"completed", "skipped"} for r in rows) else 0.0


def _papers_logged(db: Session, user: User) -> float:
    """Only marked papers count — uploading a PDF is not sitting the paper."""
    return float(
        db.scalar(
            select(func.count(PastPaper.id)).where(
                PastPaper.user_id == user.id, PastPaper.scored
            )
        )
        or 0
    )


def _paper_high_score(db: Session, user: User) -> float:
    best = db.scalar(
        select(func.max(PastPaper.percentage)).where(
            PastPaper.user_id == user.id, PastPaper.scored
        )
    )
    return float(best or 0)


def _admission_sessions(db: Session, user: User) -> float:
    return float(
        db.scalar(
            select(func.count(StudySession.id)).where(
                StudySession.user_id == user.id,
                StudySession.kind == "admission",
                StudySession.status == "completed",
            )
        )
        or 0
    )


def _subjects_added(_: Session, user: User) -> float:
    return float(len([s for s in user.subjects if not s.is_archived]))


DEFINITIONS: List[Definition] = [
    Definition("first_steps", "First Steps", "Complete your first study session.",
               "footprints", "bronze", 25, 1, _sessions_completed),
    Definition("daily_streak", "Daily Streak", "Study on two consecutive days.",
               "flame", "bronze", 30, 2, _streak),
    Definition("streak_7", "7 Day Streak", "Study every day for a week.",
               "flame", "silver", 100, 7, _streak),
    Definition("streak_30", "30 Day Streak", "Study every day for a month.",
               "flame", "gold", 400, 30, _streak),
    Definition("topics_10", "Getting Going", "Complete 10 syllabus topics.",
               "check-circle", "bronze", 50, 10, _topics_completed),
    Definition("topics_100", "100 Topics Completed", "Complete 100 syllabus topics.",
               "library", "gold", 500, 100, _topics_completed),
    Definition("subject_complete", "Completed Subject",
               "Finish every topic in one subject.", "graduation-cap", "gold", 350,
               1, _subjects_finished),
    Definition("perfect_week", "Perfect Week",
               "Complete every scheduled session for a full week.", "sparkles",
               "silver", 200, 1, _perfect_week),
    Definition("sessions_50", "Consistency", "Complete 50 study sessions.",
               "calendar-check", "silver", 150, 50, _sessions_completed),
    Definition("hours_50", "Half Century", "Log 50 hours of focused study.",
               "clock", "silver", 180, 50, _hours_studied),
    Definition("hours_200", "Marathon", "Log 200 hours of focused study.",
               "trophy", "gold", 600, 200, _hours_studied),
    Definition("papers_5", "Paper Trail", "Log 5 past papers.",
               "file-text", "bronze", 75, 5, _papers_logged),
    Definition("paper_ace", "Top Marks", "Score 90% or higher on a past paper.",
               "star", "gold", 300, 90, _paper_high_score),
    Definition("admissions_10", "Admissions Ready",
               "Complete 10 admissions-test practice sessions.", "target", "silver",
               250, 10, _admission_sessions),
    Definition("all_set", "All Set Up", "Add three or more subjects.",
               "layout-grid", "bronze", 40, 3, _subjects_added),
]

DEFINITION_INDEX = {d.code: d for d in DEFINITIONS}


def ensure_achievements(db: Session, user: User) -> None:
    """Create any achievement rows the user is missing (new definitions included)."""
    existing = {a.code for a in user.achievements}
    for definition in DEFINITIONS:
        if definition.code in existing:
            continue
        db.add(
            Achievement(
                user_id=user.id,
                code=definition.code,
                name=definition.name,
                description=definition.description,
                icon=definition.icon,
                tier=definition.tier,
                xp_reward=definition.xp,
                target_value=definition.target,
            )
        )
    db.flush()


def evaluate(db: Session, user: User) -> List[Achievement]:
    """Re-measure every achievement. Returns the ones unlocked by this call."""
    ensure_achievements(db, user)
    db.refresh(user)

    newly_unlocked: List[Achievement] = []
    for achievement in user.achievements:
        definition = DEFINITION_INDEX.get(achievement.code)
        if definition is None:
            continue

        value = definition.measure(db, user)
        achievement.current_value = value
        achievement.progress = round(
            min(100.0, value / definition.target * 100) if definition.target else 0.0, 1
        )

        if achievement.unlocked_at is None and value >= definition.target:
            achievement.unlocked_at = utcnow()
            award_xp(db, user, definition.xp)
            notify(
                db,
                user,
                title=f"Achievement unlocked — {definition.name}",
                message=f"{definition.description} +{definition.xp} XP",
                kind="achievement",
                link="/app/achievements",
            )
            log_activity(
                db,
                user,
                f"Unlocked “{definition.name}” (+{definition.xp} XP)",
                kind="achievement",
                icon="award",
            )
            newly_unlocked.append(achievement)

        db.add(achievement)

    db.flush()
    return newly_unlocked
