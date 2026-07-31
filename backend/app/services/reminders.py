"""The daily plan email behind the "Email reminders" setting.

Until this existed the setting was the only control in the app that promised
something nothing implemented: a student could switch it on and never receive
anything.

There is no scheduler inside the process on purpose. A free Render web service
spins down when idle, so a timer thread would simply not be running at 07:00,
and Render's cron jobs are a paid feature. Instead this is a plain function with
two triggers, either of which can run it: `python -m scripts.send_reminders`, or
`POST /api/v1/tasks/daily-reminders` for an external scheduler such as the
GitHub Actions workflow in .github/workflows.

Running it twice is safe. `UserSettings.last_reminder_sent_on` records the day
each student was last emailed, so a second run the same day is a no-op.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import StudySession, User, UserSettings
from app.services import email as email_service

logger = logging.getLogger(__name__)


@dataclass
class ReminderRun:
    """What a sweep did, for the CLI, the endpoint and the logs."""

    day: date
    opted_in: int = 0
    sent: int = 0
    already_sent: int = 0
    no_sessions: int = 0
    failed: int = 0
    recipients: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "day": self.day.isoformat(),
            "opted_in": self.opted_in,
            "sent": self.sent,
            "already_sent": self.already_sent,
            "no_sessions": self.no_sessions,
            "failed": self.failed,
        }


def send_daily_reminders(
    db: Session, for_date: Optional[date] = None, dry_run: bool = False
) -> ReminderRun:
    """Email that day's schedule to everyone who opted in and has one."""
    day = for_date or date.today()
    run = ReminderRun(day=day)

    if not email_service.settings.email_enabled:
        # Better to say so once than to mark everyone as emailed and send
        # nothing, which is what a naive implementation would do.
        logger.error(
            "Email is not configured, so no daily reminders were sent for %s.", day
        )
        return run

    users = db.scalars(
        select(User)
        .join(UserSettings, UserSettings.user_id == User.id)
        .where(User.is_active, UserSettings.email_reminders.is_(True))
        .options(selectinload(User.settings))
    ).all()
    run.opted_in = len(users)

    for user in users:
        settings_row = user.settings
        if settings_row is None:
            continue
        if settings_row.last_reminder_sent_on == day:
            run.already_sent += 1
            continue

        sessions = db.scalars(
            select(StudySession)
            .where(
                StudySession.user_id == user.id,
                StudySession.session_date == day,
                StudySession.status == "pending",
            )
            .order_by(StudySession.start_time)
            .options(selectinload(StudySession.subject))
        ).all()
        if not sessions:
            # No email for an empty day: a message saying "nothing scheduled" is
            # the fastest way to teach someone to ignore these.
            run.no_sessions += 1
            continue

        if dry_run:
            run.sent += 1
            run.recipients.append(user.email)
            continue

        ok = email_service.send_daily_plan(user.email, user.name, day, list(sessions))
        if not ok:
            # Deliberately not stamping the day, so a transient provider failure
            # is retried by the next run rather than silently skipped forever.
            run.failed += 1
            continue

        settings_row.last_reminder_sent_on = day
        db.add(settings_row)
        run.sent += 1
        run.recipients.append(user.email)

    if not dry_run:
        db.commit()

    logger.info("Daily reminders for %s: %s", day, run.as_dict())
    return run
