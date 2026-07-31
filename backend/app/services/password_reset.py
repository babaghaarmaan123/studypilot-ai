"""Issuing and checking the one-time codes behind "forgot my password".

The rules that make a six digit code safe are all here rather than spread
through the endpoint: a short expiry, a hard cap on guesses, one use per code,
only one live code per account, and a minimum gap between sends.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import PasswordResetCode, User

CODE_LENGTH = 6


def generate_code() -> str:
    """A zero-padded six digit code from a cryptographic source."""
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    """SQLite hands back naive datetimes even for timezone-aware columns."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _live_codes(db: Session, user: User) -> list[PasswordResetCode]:
    """Unused codes for this user, newest first, expired ones included."""
    return list(
        db.scalars(
            select(PasswordResetCode)
            .where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.used_at.is_(None),
            )
            .order_by(PasswordResetCode.id.desc())
        )
    )


def seconds_until_resend(db: Session, user: User) -> int:
    """How long the caller must wait before another code may be sent."""
    latest = db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id)
        .order_by(PasswordResetCode.id.desc())
        .limit(1)
    )
    if latest is None or latest.created_at is None:
        return 0
    elapsed = (_now() - _as_aware(latest.created_at)).total_seconds()
    return max(0, int(settings.RESET_CODE_RESEND_SECONDS - elapsed))


def issue_code(db: Session, user: User) -> Optional[str]:
    """Create and store a fresh code, returning the plaintext to email.

    Returns None when a code was sent too recently, so a caller cannot be used
    to flood somebody's inbox by submitting the form repeatedly. Any earlier
    unused code is discarded, so the newest email is always the one that works
    and an old message cannot be replayed.
    """
    if seconds_until_resend(db, user) > 0:
        return None

    for stale in _live_codes(db, user):
        db.delete(stale)

    code = generate_code()
    db.add(
        PasswordResetCode(
            user_id=user.id,
            code_hash=hash_password(code),
            expires_at=_now() + timedelta(minutes=settings.RESET_CODE_EXPIRE_MINUTES),
        )
    )
    db.flush()
    return code


def verify_code(db: Session, user: User, code: str) -> Tuple[bool, str]:
    """Check a submitted code. Returns (ok, reason) with reason for logging only.

    Every failure gives the caller the same message, because distinguishing
    "wrong code" from "expired" from "too many attempts" tells an attacker which
    of those they hit.
    """
    submitted = (code or "").strip().replace(" ", "")
    if not submitted:
        return False, "empty"

    candidates = _live_codes(db, user)
    if not candidates:
        return False, "no code issued"

    # Only the newest code is valid; issue_code deletes the rest, so anything
    # else here is a leftover from a race and should not be accepted.
    entry = candidates[0]

    if entry.attempts >= settings.RESET_CODE_MAX_ATTEMPTS:
        return False, "attempts exhausted"

    if _as_aware(entry.expires_at) < _now():
        return False, "expired"

    # Count the attempt before checking, so a crash mid-request cannot be used
    # to get unlimited free guesses.
    entry.attempts += 1
    db.add(entry)
    db.flush()

    if not verify_password(submitted, entry.code_hash):
        return False, "mismatch"

    entry.used_at = _now()
    db.add(entry)
    db.flush()
    return True, "ok"


def clear_codes(db: Session, user: User) -> None:
    """Drop every code for a user, after a successful reset or a login."""
    for entry in db.scalars(
        select(PasswordResetCode).where(PasswordResetCode.user_id == user.id)
    ):
        db.delete(entry)
    db.flush()
