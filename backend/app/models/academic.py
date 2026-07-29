"""Subjects, syllabus (units + topics), completion records and exams."""

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


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    curriculum: Mapped[Optional[str]] = mapped_column(String(48))
    exam_board: Mapped[Optional[str]] = mapped_column(String(64))
    colour: Mapped[str] = mapped_column(String(16), default="#6366f1")
    difficulty: Mapped[int] = mapped_column(Integer, default=3)          # 1..5
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    estimated_hours: Mapped[float] = mapped_column(Float, default=40.0)
    target_grade: Mapped[Optional[str]] = mapped_column(String(8))
    confidence: Mapped[int] = mapped_column(Integer, default=3)          # 1..5 self-rating
    is_weak: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # not_uploaded | pdf_uploaded | ready — see services/syllabus_parser.py.
    # A subject starts with no syllabus; the student uploads the official
    # specification PDF and StudyPilot extracts the unit/topic breakdown.
    syllabus_status: Mapped[str] = mapped_column(String(20), default="not_uploaded")
    syllabus_pdf_path: Mapped[Optional[str]] = mapped_column(String(255))
    syllabus_pdf_name: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="subjects")  # noqa: F821
    units: Mapped[List["Unit"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="Unit.order_index",
    )
    exams: Mapped[List["Exam"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    past_papers: Mapped[List["PastPaper"]] = relationship(  # noqa: F821
        back_populates="subject", cascade="all, delete-orphan"
    )

    # --- Derived ----------------------------------------------------------
    @property
    def topics(self) -> List["Topic"]:
        return [topic for unit in self.units for topic in unit.topics]

    @property
    def completion_percentage(self) -> float:
        topics = self.topics
        if not topics:
            return 0.0
        done = sum(1 for t in topics if t.status == "completed")
        return round(done / len(topics) * 100, 1)

    @property
    def hours_remaining(self) -> float:
        return round(
            sum(t.estimated_hours for t in self.topics if t.status != "completed"), 1
        )


class Unit(Base, TimestampMixin):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    subject: Mapped["Subject"] = relationship(back_populates="units")
    topics: Mapped[List["Topic"]] = relationship(
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Topic.order_index",
    )

    @property
    def completion_percentage(self) -> float:
        if not self.topics:
            return 0.0
        done = sum(1 for t in self.topics if t.status == "completed")
        return round(done / len(self.topics) * 100, 1)


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    estimated_hours: Mapped[float] = mapped_column(Float, default=2.0)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(16), default="not_started")
    # not_started | in_progress | completed
    confidence: Mapped[int] = mapped_column(Integer, default=0)  # 0..5, set on completion
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    unit: Mapped["Unit"] = relationship(back_populates="topics")
    completions: Mapped[List["CompletedTopic"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )
    revisions: Mapped[List["RevisionPlan"]] = relationship(  # noqa: F821
        back_populates="topic", cascade="all, delete-orphan"
    )


class CompletedTopic(Base, TimestampMixin):
    """Immutable audit record — one row each time a topic is marked complete.

    Keeps analytics honest even if a topic is later re-opened for revision.
    """

    __tablename__ = "completed_topics"

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
    completed_on: Mapped[date] = mapped_column(Date, nullable=False)
    minutes_spent: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=3)

    user: Mapped["User"] = relationship(back_populates="completed_topics")  # noqa: F821
    topic: Mapped["Topic"] = relationship(back_populates="completions")


class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    exam_board: Mapped[Optional[str]] = mapped_column(String(64))
    exam_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    exam_time: Mapped[Optional[str]] = mapped_column(String(16))  # "09:00"
    paper: Mapped[Optional[str]] = mapped_column(String(64))
    location: Mapped[Optional[str]] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16), default="school")  # school | admission
    preparation_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="exams")  # noqa: F821
    subject: Mapped[Optional["Subject"]] = relationship(back_populates="exams")
