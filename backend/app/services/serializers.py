"""ORM -> response-model mapping.

Kept in one place so every endpoint returns identically shaped objects; the
frontend can then rely on `subject_colour` being present wherever a subject is
referenced, for example.
"""

import json
from datetime import date
from typing import List, Optional

from app.models import (
    Achievement,
    ActivityLog,
    Exam,
    PastPaper,
    RevisionPlan,
    StudyPlan,
    StudySession,
    Subject,
    Topic,
    Unit,
    User,
)
from app.schemas.academic import ExamOut, SubjectDetail, SubjectOut, TopicOut, UnitOut
from app.schemas.auth import AdmissionExamOut, UserOut, UserSettingsOut
from app.schemas.planning import PlanOut, RevisionOut, SessionOut
from app.schemas.progress import (
    AchievementOut,
    ActivityOut,
    ExamCountdown,
    PastPaperOut,
)


def load_json_list(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        year_group=user.year_group,
        curriculum=user.curriculum,
        target_degree=user.target_degree,
        weekday_hours=user.weekday_hours,
        weekend_hours=user.weekend_hours,
        preferred_study_time=user.preferred_study_time,
        study_habits=load_json_list(user.study_habits),
        xp=user.xp,
        streak_current=user.streak_current,
        streak_longest=user.streak_longest,
        onboarding_completed=user.onboarding_completed,
        onboarding_step=user.onboarding_step,
        mentor_summary=user.mentor_summary,
        created_at=user.created_at,
        universities=[u.name for u in user.universities],
        admission_exams=[
            AdmissionExamOut.model_validate(exam) for exam in user.admission_exams
        ],
        settings=(
            UserSettingsOut.model_validate(user.settings) if user.settings else None
        ),
    )


# ---------------------------------------------------------------------------
# Academic
# ---------------------------------------------------------------------------
def topic_out(topic: Topic) -> TopicOut:
    return TopicOut.model_validate(topic)


def unit_out(unit: Unit) -> UnitOut:
    return UnitOut(
        id=unit.id,
        subject_id=unit.subject_id,
        name=unit.name,
        description=unit.description,
        order_index=unit.order_index,
        completion_percentage=unit.completion_percentage,
        topics=[topic_out(t) for t in unit.topics],
    )


def _next_exam_date(subject: Subject) -> Optional[date]:
    today = date.today()
    upcoming = sorted(e.exam_date for e in subject.exams if e.exam_date >= today)
    return upcoming[0] if upcoming else None


def subject_out(subject: Subject) -> SubjectOut:
    topics = subject.topics
    return SubjectOut(
        id=subject.id,
        name=subject.name,
        curriculum=subject.curriculum,
        exam_board=subject.exam_board,
        colour=subject.colour,
        difficulty=subject.difficulty,
        priority=subject.priority,
        estimated_hours=subject.estimated_hours,
        target_grade=subject.target_grade,
        confidence=subject.confidence,
        is_weak=subject.is_weak,
        is_archived=subject.is_archived,
        completion_percentage=subject.completion_percentage,
        hours_remaining=subject.hours_remaining,
        topic_count=len(topics),
        completed_topic_count=sum(1 for t in topics if t.status == "completed"),
        next_exam_date=_next_exam_date(subject),
        syllabus_status=subject.syllabus_status,
        syllabus_pdf_url=(
            f"/uploads/{subject.syllabus_pdf_path}" if subject.syllabus_pdf_path else None
        ),
        syllabus_pdf_name=subject.syllabus_pdf_name,
        notes=subject.notes,
    )


def subject_detail(subject: Subject) -> SubjectDetail:
    base = subject_out(subject).model_dump()
    base["units"] = [unit_out(u) for u in subject.units]
    return SubjectDetail(**base)


def exam_out(exam: Exam) -> ExamOut:
    return ExamOut(
        id=exam.id,
        title=exam.title,
        subject_id=exam.subject_id,
        subject_name=exam.subject.name if exam.subject else None,
        subject_colour=exam.subject.colour if exam.subject else None,
        exam_board=exam.exam_board,
        exam_date=exam.exam_date,
        exam_time=exam.exam_time,
        paper=exam.paper,
        location=exam.location,
        kind=exam.kind,
        preparation_percentage=exam.preparation_percentage,
        days_remaining=(exam.exam_date - date.today()).days,
        notes=exam.notes,
    )


def exam_countdown(exam: Exam) -> ExamCountdown:
    return ExamCountdown(
        id=exam.id,
        title=exam.title,
        subject_name=exam.subject.name if exam.subject else None,
        subject_colour=exam.subject.colour if exam.subject else "#6366f1",
        exam_board=exam.exam_board,
        exam_date=exam.exam_date,
        exam_time=exam.exam_time,
        days_remaining=(exam.exam_date - date.today()).days,
        preparation_percentage=exam.preparation_percentage,
        kind=exam.kind,
    )


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
def session_out(session: StudySession) -> SessionOut:
    return SessionOut(
        id=session.id,
        plan_id=session.plan_id,
        subject_id=session.subject_id,
        subject_name=session.subject.name if session.subject else None,
        subject_colour=session.subject.colour if session.subject else "#94a3b8",
        topic_id=session.topic_id,
        topic_name=session.topic.name if session.topic else None,
        title=session.title,
        description=session.description,
        session_date=session.session_date,
        start_time=session.start_time,
        duration_minutes=session.duration_minutes,
        kind=session.kind,
        status=session.status,
        priority_score=session.priority_score,
        actual_minutes=session.actual_minutes,
        completed_at=session.completed_at,
    )


def plan_out(plan: StudyPlan, session_count: Optional[int] = None) -> PlanOut:
    return PlanOut(
        id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,
        horizon_days=plan.horizon_days,
        strategy=plan.strategy,
        focus_notes=load_json_list(plan.focus_notes),
        total_hours=plan.total_hours,
        is_active=plan.is_active,
        created_at=plan.created_at,
        session_count=(
            session_count if session_count is not None else len(plan.sessions)
        ),
    )


def revision_out(revision: RevisionPlan) -> RevisionOut:
    today = date.today()
    return RevisionOut(
        id=revision.id,
        topic_id=revision.topic_id,
        topic_name=revision.topic.name if revision.topic else None,
        subject_id=revision.subject_id,
        subject_name=revision.subject.name if revision.subject else None,
        subject_colour=revision.subject.colour if revision.subject else "#6366f1",
        scheduled_date=revision.scheduled_date,
        interval_label=revision.interval_label,
        repetition_index=revision.repetition_index,
        duration_minutes=revision.duration_minutes,
        status=revision.status,
        recall_rating=revision.recall_rating,
        is_due=revision.status == "pending" and revision.scheduled_date <= today,
        is_overdue=revision.status == "pending" and revision.scheduled_date < today,
    )


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
def past_paper_out(paper: PastPaper) -> PastPaperOut:
    return PastPaperOut(
        id=paper.id,
        subject_id=paper.subject_id,
        subject_name=paper.subject.name if paper.subject else None,
        subject_colour=paper.subject.colour if paper.subject else "#6366f1",
        title=paper.title,
        exam_board=paper.exam_board,
        year=paper.year,
        paper=paper.paper,
        session_label=paper.session_label,
        date_taken=paper.date_taken,
        marks_scored=paper.marks_scored,
        marks_total=paper.marks_total,
        percentage=paper.percentage,
        grade=paper.grade,
        time_taken_minutes=paper.time_taken_minutes,
        under_timed_conditions=paper.under_timed_conditions,
        notes=paper.notes,
        scored=paper.scored,
        file_url=f"/uploads/{paper.file_path}" if paper.file_path else None,
        file_name=paper.file_name,
    )


def achievement_out(achievement: Achievement) -> AchievementOut:
    return AchievementOut(
        id=achievement.id,
        code=achievement.code,
        name=achievement.name,
        description=achievement.description,
        icon=achievement.icon,
        tier=achievement.tier,
        xp_reward=achievement.xp_reward,
        progress=achievement.progress,
        target_value=achievement.target_value,
        current_value=achievement.current_value,
        unlocked=achievement.unlocked,
        unlocked_at=achievement.unlocked_at,
    )


def activity_out(activity: ActivityLog) -> ActivityOut:
    return ActivityOut.model_validate(activity)


def sessions_out(sessions: List[StudySession]) -> List[SessionOut]:
    return [session_out(s) for s in sessions]
