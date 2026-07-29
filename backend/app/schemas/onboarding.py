"""The 10-question AI onboarding assistant payloads."""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

_CURRICULA = {"gcse", "a_level", "international_a_level"}


class OnboardingExamEntry(BaseModel):
    """Question 8 — one row of the student's exam timetable."""

    subject: str = Field(min_length=1, max_length=120)
    exam_board: Optional[str] = Field(default=None, max_length=64)
    exam_date: date
    exam_time: str = Field(default="09:00", max_length=16)
    paper: Optional[str] = Field(default=None, max_length=64)


class OnboardingSubmit(BaseModel):
    # Q1
    name: str = Field(min_length=1, max_length=120)
    # Q2
    year_group: str = Field(min_length=1, max_length=32)
    # Q3
    curriculum: str
    # Q4
    subjects: List[str] = Field(min_length=1)
    # Q5
    preparing_admission_exams: bool = False
    admission_exams: List[str] = []
    # Q6
    universities: List[str] = []
    # Q7
    target_degree: Optional[str] = None
    # Q8
    exams: List[OnboardingExamEntry] = []
    # Q9
    weekday_hours: float = Field(default=2.0, ge=0, le=16)
    weekend_hours: float = Field(default=4.0, ge=0, le=16)
    preferred_study_time: str = "evening"
    # Q10
    study_habits: List[str] = []

    @field_validator("curriculum")
    @classmethod
    def _valid_curriculum(cls, value):
        if value not in _CURRICULA:
            raise ValueError(
                "StudyPilot supports GCSE, A Level and International A Level only."
            )
        return value

    @field_validator("preferred_study_time")
    @classmethod
    def _valid_window(cls, value):
        if value not in {"morning", "afternoon", "evening", "night"}:
            raise ValueError("Preferred study time must be morning, afternoon, evening or night.")
        return value

    @field_validator("subjects")
    @classmethod
    def _dedupe_subjects(cls, value):
        seen, unique = set(), []
        for name in value:
            cleaned = name.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                unique.append(cleaned)
        if not unique:
            raise ValueError("Choose at least one subject.")
        return unique


class OnboardingDraft(BaseModel):
    """Autosave payload — accepts a partially completed wizard."""

    step: int = Field(default=0, ge=0, le=10)
    answers: Dict[str, Any] = {}


class OnboardingDraftOut(BaseModel):
    step: int
    answers: Dict[str, Any]
    completed: bool


class MentorSummary(BaseModel):
    headline: str
    summary: str
    focus_points: List[str]
    plan_id: Optional[int] = None
    subjects_created: int = 0
    topics_created: int = 0
    sessions_created: int = 0
    revisions_created: int = 0
