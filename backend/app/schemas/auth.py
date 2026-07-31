"""Authentication request / response models."""

import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

_PASSWORD_RULES = (
    "Password must be at least 8 characters and include a letter and a number."
)


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError(_PASSWORD_RULES)
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError(_PASSWORD_RULES)
    return value


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)

    _check_password = field_validator("password")(_validate_password)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Please enter your name.")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Email plus the code from that email, rather than a token from a link.

    The email address is part of the request because the code alone identifies
    nobody: six digits are not unique across accounts, so the pair is what gets
    looked up.
    """

    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    password: str = Field(max_length=128)

    _check_password = field_validator("password")(_validate_password)

    @field_validator("code")
    @classmethod
    def _tidy_code(cls, value: str) -> str:
        # Pasting from the email can bring spaces with it.
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not cleaned.isdigit():
            raise ValueError("The reset code is the six digits from your email.")
        return cleaned


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(max_length=128)

    _check_password = field_validator("new_password")(_validate_password)


class UserSettingsOut(ORMModel):
    theme: str
    notifications_enabled: bool
    email_reminders: bool
    study_reminders: bool
    weekly_report: bool
    calendar_sync: bool
    auto_reschedule: bool


class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_reminders: Optional[bool] = None
    study_reminders: Optional[bool] = None
    weekly_report: Optional[bool] = None
    calendar_sync: Optional[bool] = None
    auto_reschedule: Optional[bool] = None

    @field_validator("theme")
    @classmethod
    def _valid_theme(cls, value):
        if value is not None and value not in {"light", "dark", "system"}:
            raise ValueError("Theme must be light, dark or system.")
        return value


class AdmissionExamOut(ORMModel):
    id: int
    code: str
    name: str
    exam_date: Optional[date] = None
    preparation_percentage: float


class UserOut(ORMModel):
    id: int
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    year_group: Optional[str] = None
    curriculum: Optional[str] = None
    target_degree: Optional[str] = None
    weekday_hours: float
    weekend_hours: float
    preferred_study_time: str
    study_habits: List[str] = []
    xp: int
    streak_current: int
    streak_longest: int
    onboarding_completed: bool
    onboarding_step: int
    mentor_summary: Optional[str] = None
    created_at: datetime
    universities: List[str] = []
    admission_exams: List[AdmissionExamOut] = []
    settings: Optional[UserSettingsOut] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    year_group: Optional[str] = None
    curriculum: Optional[str] = None
    target_degree: Optional[str] = None
    weekday_hours: Optional[float] = Field(default=None, ge=0, le=16)
    weekend_hours: Optional[float] = Field(default=None, ge=0, le=16)
    preferred_study_time: Optional[str] = None
    study_habits: Optional[List[str]] = None
    universities: Optional[List[str]] = None

    @field_validator("preferred_study_time")
    @classmethod
    def _valid_window(cls, value):
        if value is not None and value not in {
            "morning",
            "afternoon",
            "evening",
            "night",
        }:
            raise ValueError("Preferred study time is not one of the allowed windows.")
        return value

    @field_validator("curriculum")
    @classmethod
    def _valid_curriculum(cls, value):
        if value is not None and value not in {
            "gcse",
            "a_level",
            "international_a_level",
        }:
            raise ValueError(
                "StudyPilot supports GCSE, A Level and International A Level only."
            )
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut
