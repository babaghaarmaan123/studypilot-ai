"""Past papers, achievements, notifications and the activity feed."""

from datetime import date, datetime
from typing import Optional

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


class PastPaper(Base, TimestampMixin):
    __tablename__ = "past_papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    exam_board: Mapped[Optional[str]] = mapped_column(String(64))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    paper: Mapped[Optional[str]] = mapped_column(String(64))
    session_label: Mapped[Optional[str]] = mapped_column(String(32))  # e.g. "June"
    date_taken: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marks_scored: Mapped[float] = mapped_column(Float, default=0.0)
    marks_total: Mapped[float] = mapped_column(Float, default=100.0)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[Optional[str]] = mapped_column(String(8))
    time_taken_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    under_timed_conditions: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # A paper uploaded from its PDF starts unscored: the student adds their
    # marks afterwards. Unscored papers are excluded from the averages and the
    # improvement trend so a 0% placeholder never drags the graph down.
    scored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(255))
    file_name: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="past_papers")  # noqa: F821
    subject: Mapped["Subject"] = relationship(back_populates="past_papers")  # noqa: F821


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    icon: Mapped[str] = mapped_column(String(48), default="award")
    tier: Mapped[str] = mapped_column(String(16), default="bronze")
    xp_reward: Mapped[int] = mapped_column(Integer, default=50)
    progress: Mapped[float] = mapped_column(Float, default=0.0)   # 0..100
    target_value: Mapped[float] = mapped_column(Float, default=1.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="achievements")  # noqa: F821

    @property
    def unlocked(self) -> bool:
        return self.unlocked_at is not None


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(24), default="info")
    # info | success | warning | exam | achievement
    link: Mapped[Optional[str]] = mapped_column(String(255))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    user: Mapped["User"] = relationship(back_populates="notifications")  # noqa: F821


class ActivityLog(Base, TimestampMixin):
    """Powers the "Recent Activity" card on the dashboard."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="general")
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="activity")
    meta: Mapped[Optional[str]] = mapped_column(Text)  # JSON blob

    user: Mapped["User"] = relationship(back_populates="activities")  # noqa: F821
