"""Study plan, session and revision schemas."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

_SESSION_KINDS = {"study", "revision", "admission", "past_paper", "break"}
_SESSION_STATUSES = {"pending", "completed", "missed", "skipped"}


class SessionOut(ORMModel):
    id: int
    plan_id: Optional[int] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_colour: Optional[str] = None
    topic_id: Optional[int] = None
    topic_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    session_date: date
    start_time: str
    duration_minutes: int
    kind: str
    status: str
    priority_score: float
    actual_minutes: int
    completed_at: Optional[datetime] = None


class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    session_date: date
    start_time: str = "17:00"
    duration_minutes: int = Field(default=60, ge=10, le=480)
    kind: str = "study"
    description: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def _valid_kind(cls, value):
        if value not in _SESSION_KINDS:
            raise ValueError(f"Kind must be one of {sorted(_SESSION_KINDS)}.")
        return value


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    session_date: Optional[date] = None
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, ge=10, le=480)
    kind: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value):
        if value is not None and value not in _SESSION_STATUSES:
            raise ValueError(f"Status must be one of {sorted(_SESSION_STATUSES)}.")
        return value


class SessionComplete(BaseModel):
    actual_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    mark_topic_complete: bool = False
    confidence: int = Field(default=3, ge=1, le=5)


class PlanOut(ORMModel):
    id: int
    start_date: date
    end_date: date
    horizon_days: int
    strategy: Optional[str] = None
    focus_notes: List[str] = []
    total_hours: float
    is_active: bool
    created_at: datetime
    session_count: int = 0


class PlanGenerateRequest(BaseModel):
    horizon_days: int = Field(default=28, ge=7, le=120)
    start_date: Optional[date] = None
    replace_existing: bool = True


class PlanWithSessions(PlanOut):
    sessions: List[SessionOut] = []


class DayPlan(BaseModel):
    date: date
    label: str
    total_minutes: int
    completed_minutes: int
    sessions: List[SessionOut] = []


class WeekPlan(BaseModel):
    week_start: date
    week_end: date
    total_hours: float
    completed_hours: float
    days: List[DayPlan] = []


class RevisionOut(ORMModel):
    id: int
    topic_id: int
    topic_name: Optional[str] = None
    subject_id: int
    subject_name: Optional[str] = None
    subject_colour: Optional[str] = None
    scheduled_date: date
    interval_label: str
    repetition_index: int
    duration_minutes: int
    status: str
    recall_rating: Optional[int] = None
    is_due: bool = False
    is_overdue: bool = False


class RevisionComplete(BaseModel):
    recall_rating: int = Field(default=3, ge=1, le=5)


class RegenerateResponse(BaseModel):
    plan: PlanOut
    missed_sessions_rescheduled: int
    message: str
