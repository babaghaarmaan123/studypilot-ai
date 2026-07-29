"""Activity feed, notifications and study-streak bookkeeping."""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ActivityLog, Notification, User


def log_activity(
    db: Session,
    user: User,
    message: str,
    kind: str = "general",
    icon: str = "activity",
    commit: bool = False,
) -> ActivityLog:
    entry = ActivityLog(user_id=user.id, message=message, kind=kind, icon=icon)
    db.add(entry)
    if commit:
        db.commit()
    return entry


def notify(
    db: Session,
    user: User,
    title: str,
    message: str = "",
    kind: str = "info",
    link: Optional[str] = None,
    commit: bool = False,
) -> Optional[Notification]:
    """Create an in-app notification unless the student has muted them."""
    if user.settings and not user.settings.notifications_enabled:
        return None
    note = Notification(
        user_id=user.id, title=title, message=message, kind=kind, link=link
    )
    db.add(note)
    if commit:
        db.commit()
    return note


def touch_streak(db: Session, user: User, on_day: Optional[date] = None) -> bool:
    """Register study activity for `on_day` and roll the streak forward.

    Returns True when the streak counter changed, so callers can decide whether
    to congratulate the student.
    """
    today = on_day or date.today()
    previous = user.last_study_date

    if previous == today:
        return False

    if previous is not None and previous == today - timedelta(days=1):
        user.streak_current += 1
    elif previous is not None and previous > today:
        # Backdated entry — leave the streak alone.
        return False
    else:
        user.streak_current = 1

    user.last_study_date = today
    user.streak_longest = max(user.streak_longest, user.streak_current)
    db.add(user)
    return True


def award_xp(db: Session, user: User, amount: int) -> int:
    user.xp = max(0, user.xp + amount)
    db.add(user)
    return user.xp


def level_for_xp(xp: int) -> int:
    """250 XP per level, starting at level 1."""
    return max(1, xp // 250 + 1)


def xp_progress(xp: int) -> tuple[int, int, int]:
    """Return (level, xp_into_level, xp_needed_for_next_level)."""
    level = level_for_xp(xp)
    into = xp - (level - 1) * 250
    return level, into, 250
