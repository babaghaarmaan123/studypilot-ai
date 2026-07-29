"""Composes the dashboard payload from every other service."""

from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityLog, StudySession, User
from app.schemas.progress import DashboardOut
from app.services import planner, revision as revision_service
from app.services.activity import xp_progress
from app.services.serializers import activity_out, exam_countdown, session_out


def _greeting(now: datetime, name: str) -> str:
    hour = now.hour
    if hour < 12:
        part = "Good morning"
    elif hour < 17:
        part = "Good afternoon"
    elif hour < 22:
        part = "Good evening"
    else:
        part = "Still going"
    first = (name or "there").split()[0]
    return f"{part}, {first}"


def build(db: Session, user: User) -> DashboardOut:
    today = date.today()
    now = datetime.now()

    # Housekeeping the dashboard is the natural place to run.
    planner.mark_missed_sessions(db, user, today)
    planner.recalculate_exam_readiness(db, user)
    db.commit()

    todays_sessions: List[StudySession] = list(
        db.scalars(
            select(StudySession)
            .where(
                StudySession.user_id == user.id,
                StudySession.session_date == today,
            )
            .order_by(StudySession.start_time)
        ).all()
    )

    goal_minutes = sum(s.duration_minutes for s in todays_sessions)
    done_minutes = sum(
        (s.actual_minutes or s.duration_minutes)
        for s in todays_sessions
        if s.status == "completed"
    )
    remaining_minutes = sum(
        s.duration_minutes for s in todays_sessions if s.status == "pending"
    )

    upcoming = sorted(
        (e for e in user.exams if e.exam_date >= today and e.kind == "school"),
        key=lambda e: e.exam_date,
    )[:6]
    admission_exams = sorted(
        (e for e in user.exams if e.exam_date >= today and e.kind == "admission"),
        key=lambda e: e.exam_date,
    )[:6]

    topics = [t for subject in user.subjects for t in subject.topics]
    topics_done = sum(1 for t in topics if t.status == "completed")

    weak = [
        {
            "id": s.id,
            "name": s.name,
            "colour": s.colour,
            "completion": s.completion_percentage,
            "difficulty": s.difficulty,
            "hours_remaining": s.hours_remaining,
        }
        for s in user.subjects
        if s.is_weak and not s.is_archived
    ][:5]

    activities = list(
        db.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user.id)
            .order_by(ActivityLog.created_at.desc())
            .limit(8)
        ).all()
    )

    missed = len(
        db.scalars(
            select(StudySession).where(
                StudySession.user_id == user.id,
                StudySession.status == "missed",
                StudySession.session_date >= today - timedelta(days=14),
            )
        ).all()
    )

    monday = today - timedelta(days=today.weekday())
    week_sessions = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.session_date >= monday,
            StudySession.session_date <= monday + timedelta(days=6),
            StudySession.status == "completed",
        )
    ).all()
    week_hours = round(
        sum((s.actual_minutes or s.duration_minutes) for s in week_sessions) / 60, 1
    )

    level, _, _ = xp_progress(user.xp)

    return DashboardOut(
        greeting=_greeting(now, user.name),
        name=user.name,
        date=today,
        streak_current=user.streak_current,
        streak_longest=user.streak_longest,
        xp=user.xp,
        level=level,
        todays_goal_minutes=goal_minutes,
        todays_completed_minutes=done_minutes,
        todays_progress=(
            round(done_minutes / goal_minutes * 100, 1) if goal_minutes else 0.0
        ),
        hours_remaining_today=round(remaining_minutes / 60, 1),
        overall_progress=(
            round(topics_done / len(topics) * 100, 1) if topics else 0.0
        ),
        topics_completed=topics_done,
        topics_total=len(topics),
        sessions_today=[session_out(s) for s in todays_sessions],
        upcoming_exams=[exam_countdown(e) for e in upcoming],
        admission_countdowns=[exam_countdown(e) for e in admission_exams],
        weak_subjects=weak,
        recent_activity=[activity_out(a) for a in activities],
        revisions_due=len(revision_service.due_revisions(db, user, today)),
        missed_sessions=missed,
        mentor_summary=user.mentor_summary,
        week_hours=week_hours,
        week_target_hours=round(user.weekday_hours * 5 + user.weekend_hours * 2, 1),
    )
