"""Password hashing and JWT issuing / verification."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from jwt import PyJWTError

from app.core.config import settings

# bcrypt has a hard 72-byte limit on the input password.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password with a per-password bcrypt salt."""
    payload = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(payload, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time verification of a plaintext password against a hash."""
    try:
        payload = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(payload, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str, expires_minutes: int, token_type: str, extra: Optional[Dict] = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, remember_me: bool = False) -> str:
    minutes = (
        settings.REMEMBER_ME_EXPIRE_MINUTES
        if remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _create_token(str(user_id), minutes, "access")


def create_reset_token(user_id: int) -> str:
    return _create_token(str(user_id), settings.RESET_TOKEN_EXPIRE_MINUTES, "reset")


def decode_token(token: str, expected_type: str = "access") -> Optional[int]:
    """Return the user id encoded in `token`, or None if it is not usable."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except PyJWTError:
        return None

    if payload.get("type") != expected_type:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
