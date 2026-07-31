"""User account, preferences and university/admission ambitions."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="Student")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512))

    # --- Academic profile (captured during onboarding) ---------------------
    year_group: Mapped[Optional[str]] = mapped_column(String(32))
    curriculum: Mapped[Optional[str]] = mapped_column(String(48))
    target_degree: Mapped[Optional[str]] = mapped_column(String(120))

    # --- Study capacity ----------------------------------------------------
    weekday_hours: Mapped[float] = mapped_column(default=2.0, nullable=False)
    weekend_hours: Mapped[float] = mapped_column(default=4.0, nullable=False)
    preferred_study_time: Mapped[str] = mapped_column(String(24), default="evening")
    study_habits: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of habit codes

    # --- Gamification ------------------------------------------------------
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_longest: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_study_date: Mapped[Optional[date]] = mapped_column(Date)

    # --- Lifecycle ---------------------------------------------------------
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onboarding_draft: Mapped[Optional[str]] = mapped_column(Text)  # autosaved JSON
    mentor_summary: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # --- Relationships -----------------------------------------------------
    settings: Mapped[Optional["UserSettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    universities: Mapped[List["TargetUniversity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    admission_exams: Mapped[List["AdmissionExam"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subjects: Mapped[List["Subject"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    exams: Mapped[List["Exam"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    study_plans: Mapped[List["StudyPlan"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["StudySession"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    revisions: Mapped[List["RevisionPlan"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    past_papers: Mapped[List["PastPaper"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[List["Achievement"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    activities: Mapped[List["ActivityLog"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    completed_topics: Mapped[List["CompletedTopic"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    reset_codes: Mapped[List["PasswordResetCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetCode(Base, TimestampMixin):
    """A one-time code emailed to somebody who has forgotten their password.

    Only the hash is stored, for the same reason passwords are hashed: a leaked
    database must not hand out working reset codes. `attempts` is what stops a
    six digit code being guessed by brute force, and `used_at` is what stops one
    code resetting a password twice.
    """

    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="reset_codes")


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    theme: Mapped[str] = mapped_column(String(16), default="system")  # light | dark | system
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    study_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_report: Mapped[bool] = mapped_column(Boolean, default=True)
    calendar_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_reschedule: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="settings")


class TargetUniversity(Base, TimestampMixin):
    __tablename__ = "target_universities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)

    user: Mapped["User"] = relationship(back_populates="universities")


class AdmissionExam(Base, TimestampMixin):
    """A university admissions test the student is preparing for (TMUA, UCAT...)."""

    __tablename__ = "admission_exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    preparation_percentage: Mapped[float] = mapped_column(default=0.0)

    user: Mapped["User"] = relationship(back_populates="admission_exams")
