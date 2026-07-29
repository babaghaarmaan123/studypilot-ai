"""Aggregations behind the analytics dashboard."""

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompletedTopic, PastPaper, StudySession, User
from app.services import revision as revision_service

_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _completed_sessions(db: Session, user: User, since: date) -> List[StudySession]:
    return list(
        db.scalars(
            select(StudySession).where(
                StudySession.user_id == user.id,
                StudySession.status == "completed",
                StudySession.session_date >= since,
            )
        ).all()
    )


def _minutes(session: StudySession) -> int:
    return session.actual_minutes or session.duration_minutes


def weekly_hours(db: Session, user: User) -> List[Dict]:
    """Hours studied on each day of the current week (Monday first)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sessions = _completed_sessions(db, user, monday)

    buckets = defaultdict(float)
    for session in sessions:
        buckets[session.session_date] += _minutes(session) / 60

    return [
        {
            "label": _WEEKDAYS[i],
            "value": round(buckets.get(monday + timedelta(days=i), 0.0), 2),
            "date": (monday + timedelta(days=i)).isoformat(),
        }
        for i in range(7)
    ]


def monthly_hours(db: Session, user: User, weeks: int = 12) -> List[Dict]:
    """Hours per ISO week over the last `weeks` weeks."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start = monday - timedelta(weeks=weeks - 1)
    sessions = _completed_sessions(db, user, start)

    buckets = defaultdict(float)
    for session in sessions:
        week_start = session.session_date - timedelta(
            days=session.session_date.weekday()
        )
        buckets[week_start] += _minutes(session) / 60

    series = []
    for i in range(weeks):
        week_start = start + timedelta(weeks=i)
        series.append(
            {
                "label": week_start.strftime("%d %b"),
                "value": round(buckets.get(week_start, 0.0), 2),
                "date": week_start.isoformat(),
            }
        )
    return series


def subject_distribution(db: Session, user: User, days: int = 30) -> List[Dict]:
    """Share of study time per subject over the last `days` days."""
    since = date.today() - timedelta(days=days)
    sessions = _completed_sessions(db, user, since)

    buckets = defaultdict(float)
    for session in sessions:
        if session.subject_id:
            buckets[session.subject_id] += _minutes(session) / 60

    total = sum(buckets.values()) or 1.0
    rows = []
    for subject in user.subjects:
        hours = buckets.get(subject.id, 0.0)
        if hours == 0 and subject.is_archived:
            continue
        rows.append(
            {
                "subject_id": subject.id,
                "name": subject.name,
                "colour": subject.colour,
                "hours": round(hours, 2),
                "share": round(hours / total * 100, 1),
            }
        )
    rows.sort(key=lambda r: r["hours"], reverse=True)
    return rows


def completion_by_subject(user: User) -> List[Dict]:
    return [
        {
            "subject_id": subject.id,
            "name": subject.name,
            "colour": subject.colour,
            "completion": subject.completion_percentage,
            "topics_total": len(subject.topics),
            "topics_done": sum(1 for t in subject.topics if t.status == "completed"),
            "hours_remaining": subject.hours_remaining,
            "is_weak": subject.is_weak,
            "difficulty": subject.difficulty,
        }
        for subject in user.subjects
        if not subject.is_archived
    ]


def streak_calendar(db: Session, user: User, days: int = 84) -> List[Dict]:
    """Per-day study minutes for the heatmap (12 weeks by default)."""
    start = date.today() - timedelta(days=days - 1)
    sessions = _completed_sessions(db, user, start)

    buckets = defaultdict(int)
    for session in sessions:
        buckets[session.session_date] += _minutes(session)

    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "minutes": buckets.get(start + timedelta(days=i), 0),
        }
        for i in range(days)
    ]


def exam_readiness(user: User) -> List[Dict]:
    today = date.today()
    rows = []
    for exam in user.exams:
        if exam.kind != "school" or exam.exam_date < today:
            continue
        rows.append(
            {
                "exam_id": exam.id,
                "title": exam.title,
                "subject": exam.subject.name if exam.subject else exam.title,
                "colour": exam.subject.colour if exam.subject else "#6366f1",
                "readiness": exam.preparation_percentage,
                "days_remaining": (exam.exam_date - today).days,
                "exam_date": exam.exam_date.isoformat(),
            }
        )
    rows.sort(key=lambda r: r["days_remaining"])
    return rows


def admission_readiness(user: User) -> List[Dict]:
    today = date.today()
    return [
        {
            "code": entry.code,
            "name": entry.name,
            "readiness": entry.preparation_percentage,
            "exam_date": entry.exam_date.isoformat() if entry.exam_date else None,
            "days_remaining": (
                (entry.exam_date - today).days if entry.exam_date else None
            ),
        }
        for entry in user.admission_exams
    ]


def past_paper_trend(db: Session, user: User) -> List[Dict]:
    papers = db.scalars(
        select(PastPaper)
        # Papers uploaded but not yet marked have no score to plot.
        .where(PastPaper.user_id == user.id, PastPaper.scored)
        .order_by(PastPaper.date_taken)
    ).all()
    return [
        {
            "label": paper.date_taken.strftime("%d %b"),
            "date": paper.date_taken.isoformat(),
            "percentage": round(paper.percentage, 1),
            "subject": paper.subject.name if paper.subject else "",
            "colour": paper.subject.colour if paper.subject else "#6366f1",
            "title": paper.title,
        }
        for paper in papers
    ]


def totals(db: Session, user: User) -> Dict[str, float]:
    all_completed = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id, StudySession.status == "completed"
        )
    ).all()
    total_minutes = sum(_minutes(s) for s in all_completed)

    topics = [t for subject in user.subjects for t in subject.topics]
    done = sum(1 for t in topics if t.status == "completed")

    completed_topic_rows = db.scalars(
        select(CompletedTopic).where(CompletedTopic.user_id == user.id)
    ).all()

    missed = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id, StudySession.status == "missed"
        )
    ).all()

    scheduled = len(all_completed) + len(missed)
    return {
        "total_hours": round(total_minutes / 60, 1),
        "sessions_completed": float(len(all_completed)),
        "sessions_missed": float(len(missed)),
        "adherence": round(len(all_completed) / scheduled * 100, 1) if scheduled else 0.0,
        "topics_completed": float(done),
        "topics_total": float(len(topics)),
        "overall_completion": round(done / len(topics) * 100, 1) if topics else 0.0,
        "completion_events": float(len(completed_topic_rows)),
        "streak_current": float(user.streak_current),
        "streak_longest": float(user.streak_longest),
        "xp": float(user.xp),
    }


def build(db: Session, user: User) -> Dict:
    return {
        "weekly_hours": weekly_hours(db, user),
        "monthly_hours": monthly_hours(db, user),
        "subject_distribution": subject_distribution(db, user),
        "completion_by_subject": completion_by_subject(user),
        "streak_calendar": streak_calendar(db, user),
        "revision_progress": revision_service.revision_stats(db, user),
        "exam_readiness": exam_readiness(user),
        "admission_readiness": admission_readiness(user),
        "totals": totals(db, user),
        "past_paper_trend": past_paper_trend(db, user),
    }
