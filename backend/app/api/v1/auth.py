"""Registration, login, password reset and the current-user endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    create_reset_token,
    decode_token,
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
from app.services.achievements import ensure_achievements
from app.services.activity import log_activity
from app.services.serializers import user_out

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
    summary="Request a password reset",
    description=(
        "Always responds with 200 so the endpoint cannot be used to enumerate "
        "registered emails. In development the reset token is included in the "
        "response body; in production it would be emailed instead."
    ),
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    response = {
        "ok": True,
        "message": (
            "If an account exists for that email, a reset link is on its way."
        ),
    }
    if user is None:
        return response

    token = create_reset_token(user.id)
    if settings.DEBUG:
        # Convenience for local development — no mail server required.
        response["reset_token"] = token
    return response


@router.post(
    "/reset-password",
    response_model=Message,
    summary="Reset a password using a reset token",
)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> Message:
    user_id = decode_token(payload.token, expected_type="reset")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That reset link is invalid or has expired.",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That reset link is invalid or has expired.",
        )

    user.hashed_password = hash_password(payload.password)
    db.add(user)
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
