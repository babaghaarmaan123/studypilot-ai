"""Generated study plans, individual sessions and spaced-repetition revisions."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class StudyPlan(Base, TimestampMixin):
    """One generation run of the AI study engine."""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, default=28)
    strategy: Mapped[Optional[str]] = mapped_column(Text)   # human-readable rationale
    focus_notes: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of bullet points
    total_hours: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    regenerated_from_id: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="study_plans")  # noqa: F821
    sessions: Mapped[List["StudySession"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class StudySession(Base, TimestampMixin):
    """A single scheduled block of work on the student's timetable."""

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[str] = mapped_column(String(8), default="17:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    kind: Mapped[str] = mapped_column(String(24), default="study")
    # study | revision | admission | past_paper | break
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | completed | missed | skipped
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    plan: Mapped[Optional["StudyPlan"]] = relationship(back_populates="sessions")
    subject: Mapped[Optional["Subject"]] = relationship()  # noqa: F821
    topic: Mapped[Optional["Topic"]] = relationship()  # noqa: F821


class RevisionPlan(Base, TimestampMixin):
    """Spaced-repetition entry: 2 days, 7 days, 14 days, then a final pre-exam pass."""

    __tablename__ = "revision_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    interval_label: Mapped[str] = mapped_column(String(16))  # 2d | 7d | 14d | final
    repetition_index: Mapped[int] = mapped_column(Integer, default=1)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | completed | missed
    recall_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1..5
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="revisions")  # noqa: F821
    topic: Mapped["Topic"] = relationship(back_populates="revisions")  # noqa: F821
    subject: Mapped["Subject"] = relationship()  # noqa: F821
