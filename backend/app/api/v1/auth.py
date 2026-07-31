"""Registration, login, password reset and the current-user endpoint."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserSettings
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import Message
from app.services import email as email_service
from app.services import password_reset
from app.services.achievements import ensure_achievements
from app.services.activity import log_activity
from app.services.serializers import user_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_response(user: User, remember_me: bool = False) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, remember_me=remember_me),
        expires_in_minutes=(
            settings.REMEMBER_ME_EXPIRE_MINUTES
            if remember_me
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        user=user_out(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description=(
        "Creates the account, hashes the password with bcrypt and returns a JWT. "
        "New accounts start with `onboarding_completed = false`, so the client "
        "should route to the onboarding assistant rather than the dashboard."
    ),
)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists. Try signing in.",
        )

    user = User(
        email=email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        last_login_at=datetime.now(timezone.utc),
    )
    user.settings = UserSettings()
    db.add(user)
    db.commit()
    db.refresh(user)

    ensure_achievements(db, user)
    log_activity(db, user, "Created your StudyPilot account", kind="account", icon="user-plus")
    db.commit()
    db.refresh(user)

    return _token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in",
    description=(
        "Verifies the password and returns a JWT. Pass `remember_me` to receive a "
        "30-day token instead of the default 24-hour one."
    ),
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Same message either way — do not leak which emails are registered.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user, remember_me=payload.remember_me)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Current user",
    description="Returns the signed-in student's profile, settings and ambitions.",
)
def me(user: CurrentUser) -> UserOut:
    return user_out(user)


@router.post(
    "/forgot-password",
    summary="Email a password reset code",
    description=(
        "Emails a six digit code that expires in "
        f"{settings.RESET_CODE_EXPIRE_MINUTES} minutes.\n\n"
        "Always responds with 200, whether or not the address belongs to an "
        "account, so the endpoint cannot be used to discover who has registered. "
        "For the same reason it does not report whether the email was actually "
        "delivered.\n\n"
        "In development the code is included in the response body so the flow "
        "can be exercised without a mail server."
    ),
)
def forgot_password(
    payload: ForgotPasswordRequest, db: DbSession, background: BackgroundTasks
) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    response = {
        "ok": True,
        "message": (
            "If an account exists for that email, a reset code is on its way. "
            "It expires in "
            f"{settings.RESET_CODE_EXPIRE_MINUTES} minutes."
        ),
    }
    if user is None or not user.is_active:
        return response

    code = password_reset.issue_code(db, user)
    if code is None:
        # A code went out moments ago. Say nothing different: the student has a
        # working code in their inbox already, and reporting the throttle would
        # confirm the address is registered.
        return response
    db.commit()

    # Handed to a background task because SMTP is blocking, and a mail server
    # that takes twenty seconds to answer should not hold the request open.
    background.add_task(
        email_service.send_password_reset_code, user.email, user.name, code
    )

    if settings.DEBUG:
        response["reset_code"] = code
    return response


@router.post(
    "/reset-password",
    response_model=Message,
    summary="Reset a password using the emailed code",
)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> Message:
    # One message for every failure. Telling the caller whether the address
    # exists, whether the code was wrong, or whether it had expired hands an
    # attacker exactly the information they are probing for.
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "That code is not valid or has expired. Request a new one and try "
            "again."
        ),
    )

    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if user is None or not user.is_active:
        raise invalid

    ok, reason = password_reset.verify_code(db, user, payload.code)
    if not ok:
        db.commit()  # keep the attempt counter
        logger.info("Password reset rejected for user %s: %s", user.id, reason)
        raise invalid

    user.hashed_password = hash_password(payload.password)
    db.add(user)
    # Every other code for this account goes too, so a second email that is
    # still sitting in the inbox cannot be used afterwards.
    password_reset.clear_codes(db, user)
    log_activity(db, user, "Reset your password", kind="account", icon="key-round")
    db.commit()
    return Message(message="Password updated. You can sign in now.")


@router.post(
    "/change-password",
    response_model=Message,
    summary="Change the password of the signed-in user",
)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> Message:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is not correct.",
        )
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    log_activity(db, user, "Changed your password", kind="account", icon="key-round")
    db.commit()
    return Message(message="Password changed.")
