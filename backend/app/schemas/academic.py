"""Subject, syllabus and exam schemas."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

_PRIORITIES = {"low", "medium", "high"}
_TOPIC_STATUSES = {"not_started", "in_progress", "completed"}


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
class TopicBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    estimated_hours: float = Field(default=2.0, ge=0.25, le=60)
    difficulty: int = Field(default=3, ge=1, le=5)
    notes: Optional[str] = None


class TopicCreate(TopicBase):
    unit_id: int


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    estimated_hours: Optional[float] = Field(default=None, ge=0.25, le=60)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[str] = None
    confidence: Optional[int] = Field(default=None, ge=0, le=5)
    order_index: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value):
        if value is not None and value not in _TOPIC_STATUSES:
            raise ValueError("Status must be not_started, in_progress or completed.")
        return value


class TopicComplete(BaseModel):
    confidence: int = Field(default=3, ge=1, le=5)
    minutes_spent: int = Field(default=0, ge=0, le=1440)
    schedule_revision: bool = True


class TopicOut(ORMModel):
    id: int
    unit_id: int
    name: str
    estimated_hours: float
    difficulty: int
    status: str
    confidence: int
    order_index: int
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
class UnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = None
    order_index: int = 0


class UnitUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=160)
    description: Optional[str] = None
    order_index: Optional[int] = None


class UnitOut(ORMModel):
    id: int
    subject_id: int
    name: str
    description: Optional[str] = None
    order_index: int
    completion_percentage: float
    topics: List[TopicOut] = []


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
class SubjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    exam_board: Optional[str] = Field(default=None, max_length=64)
    colour: str = Field(default="#6366f1", pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    difficulty: int = Field(default=3, ge=1, le=5)
    priority: str = "medium"
    estimated_hours: float = Field(default=40.0, ge=1, le=1000)
    target_grade: Optional[str] = Field(default=None, max_length=8)
    confidence: int = Field(default=3, ge=1, le=5)

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, value):
        if value not in _PRIORITIES:
            raise ValueError("Priority must be low, medium or high.")
        return value


class SubjectCreate(SubjectBase):
    curriculum: Optional[str] = None
    # Syllabi are now built from an uploaded PDF, not auto-seeded — see
    # POST /subjects/{id}/syllabus-pdf. This flag is kept for the legacy
    # template-seeding endpoint only.
    seed_syllabus: bool = False


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    exam_board: Optional[str] = None
    colour: Optional[str] = Field(default=None, pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    priority: Optional[str] = None
    estimated_hours: Optional[float] = Field(default=None, ge=1, le=1000)
    target_grade: Optional[str] = None
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    is_weak: Optional[bool] = None
    is_archived: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, value):
        if value is not None and value not in _PRIORITIES:
            raise ValueError("Priority must be low, medium or high.")
        return value


class SubjectOut(ORMModel):
    id: int
    name: str
    curriculum: Optional[str] = None
    exam_board: Optional[str] = None
    colour: str
    difficulty: int
    priority: str
    estimated_hours: float
    target_grade: Optional[str] = None
    confidence: int
    is_weak: bool
    is_archived: bool
    completion_percentage: float
    hours_remaining: float
    topic_count: int = 0
    completed_topic_count: int = 0
    next_exam_date: Optional[date] = None
    syllabus_status: str = "not_uploaded"
    syllabus_pdf_url: Optional[str] = None
    syllabus_pdf_name: Optional[str] = None
    notes: Optional[str] = None


class SubjectDetail(SubjectOut):
    units: List[UnitOut] = []


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
class ExamBase(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    subject_id: Optional[int] = None
    exam_board: Optional[str] = Field(default=None, max_length=64)
    exam_date: date
    exam_time: Optional[str] = Field(default="09:00", max_length=16)
    paper: Optional[str] = Field(default=None, max_length=64)
    location: Optional[str] = Field(default=None, max_length=120)
    kind: str = "school"
    notes: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def _valid_kind(cls, value):
        if value not in {"school", "admission"}:
            raise ValueError("Exam kind must be school or admission.")
        return value


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=180)
    subject_id: Optional[int] = None
    exam_board: Optional[str] = None
    exam_date: Optional[date] = None
    exam_time: Optional[str] = None
    paper: Optional[str] = None
    location: Optional[str] = None
    kind: Optional[str] = None
    notes: Optional[str] = None


class ExamOut(ORMModel):
    id: int
    title: str
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_colour: Optional[str] = None
    exam_board: Optional[str] = None
    exam_date: date
    exam_time: Optional[str] = None
    paper: Optional[str] = None
    location: Optional[str] = None
    kind: str
    preparation_percentage: float
    days_remaining: int = 0
    notes: Optional[str] = None
