"""Dashboard, analytics, past papers, achievements and notifications."""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.academic import ExamOut
from app.schemas.common import ORMModel
from app.schemas.planning import SessionOut


# ---------------------------------------------------------------------------
# Past papers
# ---------------------------------------------------------------------------
class PastPaperCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    exam_board: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    paper: Optional[str] = Field(default=None, max_length=64)
    session_label: Optional[str] = Field(default=None, max_length=32)
    date_taken: date
    marks_scored: float = Field(ge=0)
    marks_total: float = Field(gt=0)
    grade: Optional[str] = Field(default=None, max_length=8)
    time_taken_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    under_timed_conditions: bool = True
    notes: Optional[str] = None

    @field_validator("marks_total")
    @classmethod
    def _total_positive(cls, value):
        if value <= 0:
            raise ValueError("Total marks must be greater than zero.")
        return value


class PastPaperScore(BaseModel):
    """Adding the marks to a paper that was uploaded without them."""

    marks_scored: float = Field(ge=0)
    marks_total: float = Field(gt=0)
    time_taken_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    under_timed_conditions: Optional[bool] = None


class PastPaperUpdate(BaseModel):
    title: Optional[str] = None
    exam_board: Optional[str] = None
    year: Optional[int] = None
    paper: Optional[str] = None
    session_label: Optional[str] = None
    date_taken: Optional[date] = None
    marks_scored: Optional[float] = Field(default=None, ge=0)
    marks_total: Optional[float] = Field(default=None, gt=0)
    grade: Optional[str] = None
    time_taken_minutes: Optional[int] = None
    under_timed_conditions: Optional[bool] = None
    notes: Optional[str] = None


class PastPaperOut(ORMModel):
    id: int
    subject_id: int
    subject_name: Optional[str] = None
    subject_colour: Optional[str] = None
    title: str
    exam_board: Optional[str] = None
    year: Optional[int] = None
    paper: Optional[str] = None
    session_label: Optional[str] = None
    date_taken: date
    marks_scored: float
    marks_total: float
    percentage: float
    grade: Optional[str] = None
    time_taken_minutes: Optional[int] = None
    under_timed_conditions: bool
    notes: Optional[str] = None
    scored: bool = True
    file_url: Optional[str] = None
    file_name: Optional[str] = None


class PastPaperStats(BaseModel):
    total_papers: int
    awaiting_score: int = 0
    average_percentage: float
    best_percentage: float
    latest_percentage: float
    improvement: float
    by_subject: List[Dict] = []
    trend: List[Dict] = []


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------
class AchievementOut(ORMModel):
    id: int
    code: str
    name: str
    description: str
    icon: str
    tier: str
    xp_reward: int
    progress: float
    target_value: float
    current_value: float
    unlocked: bool
    unlocked_at: Optional[datetime] = None


class AchievementSummary(BaseModel):
    xp: int
    level: int
    xp_into_level: int
    xp_for_next_level: int
    unlocked_count: int
    total_count: int
    streak_current: int
    streak_longest: int
    achievements: List[AchievementOut]


# ---------------------------------------------------------------------------
# Notifications & activity
# ---------------------------------------------------------------------------
class NotificationOut(ORMModel):
    id: int
    title: str
    message: str
    kind: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class ActivityOut(ORMModel):
    id: int
    kind: str
    message: str
    icon: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class ExamCountdown(BaseModel):
    id: int
    title: str
    subject_name: Optional[str] = None
    subject_colour: Optional[str] = None
    exam_board: Optional[str] = None
    exam_date: date
    exam_time: Optional[str] = None
    days_remaining: int
    preparation_percentage: float
    kind: str


class DashboardOut(BaseModel):
    greeting: str
    name: str
    date: date
    streak_current: int
    streak_longest: int
    xp: int
    level: int
    todays_goal_minutes: int
    todays_completed_minutes: int
    todays_progress: float
    hours_remaining_today: float
    overall_progress: float
    topics_completed: int
    topics_total: int
    sessions_today: List[SessionOut] = []
    upcoming_exams: List[ExamCountdown] = []
    admission_countdowns: List[ExamCountdown] = []
    weak_subjects: List[Dict] = []
    recent_activity: List[ActivityOut] = []
    revisions_due: int = 0
    missed_sessions: int = 0
    mentor_summary: Optional[str] = None
    week_hours: float = 0.0
    week_target_hours: float = 0.0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class SeriesPoint(BaseModel):
    label: str
    value: float


class AnalyticsOut(BaseModel):
    weekly_hours: List[SeriesPoint]
    monthly_hours: List[SeriesPoint]
    subject_distribution: List[Dict]
    completion_by_subject: List[Dict]
    streak_calendar: List[Dict]
    revision_progress: Dict[str, float]
    exam_readiness: List[Dict]
    admission_readiness: List[Dict]
    totals: Dict[str, float]
    past_paper_trend: List[Dict]


class ExamCountdownList(BaseModel):
    school: List[ExamCountdown]
    admission: List[ExamCountdown]


__all__ = [
    "PastPaperCreate",
    "PastPaperScore",
    "PastPaperUpdate",
    "PastPaperOut",
    "PastPaperStats",
    "AchievementOut",
    "AchievementSummary",
    "NotificationOut",
    "ActivityOut",
    "ExamCountdown",
    "ExamCountdownList",
    "DashboardOut",
    "AnalyticsOut",
    "SeriesPoint",
    "ExamOut",
]
