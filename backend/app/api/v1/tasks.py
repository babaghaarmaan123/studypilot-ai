"""Endpoints for a scheduler to call, not for a signed-in user.

A free Render web service has no cron and spins down when idle, so scheduled
work has to be triggered from outside. These endpoints exist for that, and are
guarded by a shared secret rather than a JWT because no user owns them.

With `TASK_SECRET` unset every request is refused: an unauthenticated trigger
would be a way for anyone to make the app email its entire user base at will,
and to burn a day's sending quota in a few seconds.
"""

from __future__ import annotations

import hmac
from datetime import date
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.core.config import settings
from app.core.deps import DbSession
from app.services import reminders

router = APIRouter(prefix="/tasks", tags=["Scheduled tasks"])


def _authorise(provided: Optional[str]) -> None:
    if not settings.TASK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Scheduled tasks are disabled because TASK_SECRET is not set on "
                "the server."
            ),
        )
    # compare_digest, so a wrong key cannot be recovered one character at a time
    # by timing the response.
    if not provided or not hmac.compare_digest(provided, settings.TASK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid task key.",
        )


@router.post(
    "/daily-reminders",
    summary="Email today's plan to everyone who opted in",
    description=(
        "Sends each student with `email_reminders` enabled a list of that day's "
        "pending sessions. Students with nothing scheduled are skipped.\n\n"
        "Safe to call more than once: each student is stamped with the day they "
        "were last emailed, so a repeat run the same day sends nothing. A send "
        "that fails is deliberately left unstamped so the next run retries it.\n\n"
        "Authenticate with the `X-Task-Key` header matching `TASK_SECRET`."
    ),
)
def daily_reminders(
    db: DbSession,
    x_task_key: Optional[str] = Header(default=None, alias="X-Task-Key"),
    day: Optional[date] = Query(
        default=None, description="Defaults to today. Mainly useful for testing."
    ),
    dry_run: bool = Query(
        default=False, description="Report who would be emailed without sending."
    ),
) -> dict:
    _authorise(x_task_key)
    run = reminders.send_daily_reminders(db, for_date=day, dry_run=dry_run)
    return {"ok": True, "dry_run": dry_run, **run.as_dict()}
