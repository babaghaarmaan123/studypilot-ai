"""Study plan generation and the day / week / month timetable views."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.base import utcnow
from app.models import StudyPlan, StudySession, Subject, Topic
from app.schemas.common import Message
from app.schemas.planning import (
    DayPlan,
    PlanGenerateRequest,
    PlanOut,
    PlanWithSessions,
    RegenerateResponse,
    SessionComplete,
    SessionCreate,
    SessionOut,
    SessionUpdate,
    WeekPlan,
)
from app.services import mentor, planner
from app.services import subjects as subject_service
from app.services.achievements import evaluate
from app.services.activity import award_xp, log_activity, touch_streak
from app.services.serializers import plan_out, session_out

router = APIRouter(prefix="/plans", tags=["Study planner"])


def _get_session(db, user, session_id: int) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found."
        )
    return session


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------
@router.post(
    "/generate",
    response_model=PlanWithSessions,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalised study plan",
    description=(
        "Runs the AI study engine over your exam dates, available hours, subject "
        "difficulty, remaining syllabus, admissions tests, completed topics and "
        "weak subjects. Pending future sessions from the previous plan are "
        "replaced; completed and missed sessions are always kept."
    ),
)
def generate(
    payload: PlanGenerateRequest, user: CurrentUser, db: DbSession
) -> PlanWithSessions:
    if not any(not s.is_archived for s in user.subjects):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one subject before generating a plan.",
        )

    subject_service.recalculate_weak_subjects(db, user)
    plan = planner.generate_plan(
        db,
        user,
        horizon_days=payload.horizon_days,
        start_date=payload.start_date,
        replace_existing=payload.replace_existing,
    )
    mentor.refresh_summary(db, user, plan)
    log_activity(
        db,
        user,
        f"Generated a new {plan.horizon_days}-day study plan",
        kind="plan",
        icon="wand-sparkles",
    )
    db.commit()
    db.refresh(plan)

    body = plan_out(plan).model_dump()
    body["sessions"] = [session_out(s) for s in sorted(
        plan.sessions, key=lambda s: (s.session_date, s.start_time)
    )]
    return PlanWithSessions(**body)


@router.get("/active", response_model=Optional[PlanOut], summary="Current active plan")
def get_active(user: CurrentUser, db: DbSession) -> Optional[PlanOut]:
    plan = planner.active_plan(db, user)
    return plan_out(plan) if plan else None


@router.get("/history", response_model=List[PlanOut], summary="Previous plans")
def history(user: CurrentUser, db: DbSession) -> List[PlanOut]:
    plans = db.scalars(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id)
        .order_by(StudyPlan.created_at.desc())
        .limit(20)
    ).all()
    return [plan_out(p) for p in plans]


@router.post(
    "/regenerate",
    response_model=RegenerateResponse,
    summary="Rebuild the plan around missed sessions",
    description=(
        "Marks overdue pending sessions as missed and, once at least three have "
        "piled up, redistributes the outstanding work across the remaining days."
    ),
)
def regenerate(user: CurrentUser, db: DbSession) -> RegenerateResponse:
    plan, missed = planner.regenerate_after_missed(db, user)
    if plan is None:
        current = planner.active_plan(db, user)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active plan yet. Generate one first.",
            )
        db.commit()
        return RegenerateResponse(
            plan=plan_out(current),
            missed_sessions_rescheduled=missed,
            message=(
                f"{missed} missed session(s) recorded. Not enough to justify "
                "reshuffling your plan yet."
            )
            if missed
            else "You're on track. Nothing needed rescheduling.",
        )

    mentor.refresh_summary(db, user, plan)
    log_activity(
        db,
        user,
        f"Plan rebuilt after {missed} missed session(s)",
        kind="plan",
        icon="refresh-cw",
    )
    db.commit()
    db.refresh(plan)
    return RegenerateResponse(
        plan=plan_out(plan),
        missed_sessions_rescheduled=missed,
        message=(
            f"Rescheduled around {missed} missed session(s). Your remaining "
            "syllabus has been spread across the days you have left."
        ),
    )


# ---------------------------------------------------------------------------
# Timetable views
# ---------------------------------------------------------------------------
@router.get("/today", response_model=List[SessionOut], summary="Today's study plan")
def today(user: CurrentUser, db: DbSession) -> List[SessionOut]:
    planner.mark_missed_sessions(db, user)
    db.commit()
    sessions = planner.sessions_between(db, user, date.today(), date.today())
    return [session_out(s) for s in sessions]


@router.get("/week", response_model=WeekPlan, summary="Weekly planner")
def week(
    user: CurrentUser,
    db: DbSession,
    start: Optional[date] = Query(
        None, description="Any date in the week; defaults to this week"
    ),
) -> WeekPlan:
    anchor = start or date.today()
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    sessions = planner.sessions_between(db, user, monday, sunday)

    days: List[DayPlan] = []
    total = completed = 0
    for offset in range(7):
        day = monday + timedelta(days=offset)
        day_sessions = [s for s in sessions if s.session_date == day]
        day_total = sum(s.duration_minutes for s in day_sessions)
        day_done = sum(
            (s.actual_minutes or s.duration_minutes)
            for s in day_sessions
            if s.status == "completed"
        )
        total += day_total
        completed += day_done
        days.append(
            DayPlan(
                date=day,
                label=day.strftime("%A"),
                total_minutes=day_total,
                completed_minutes=day_done,
                sessions=[session_out(s) for s in day_sessions],
            )
        )

    return WeekPlan(
        week_start=monday,
        week_end=sunday,
        total_hours=round(total / 60, 1),
        completed_hours=round(completed / 60, 1),
        days=days,
    )


@router.get("/month", response_model=List[DayPlan], summary="Monthly planner")
def month(
    user: CurrentUser,
    db: DbSession,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[DayPlan]:
    import calendar

    today_date = date.today()
    y = year or today_date.year
    m = month or today_date.month
    _, days_in_month = calendar.monthrange(y, m)
    start = date(y, m, 1)
    end = date(y, m, days_in_month)

    sessions = planner.sessions_between(db, user, start, end)
    result: List[DayPlan] = []
    for offset in range(days_in_month):
        day = start + timedelta(days=offset)
        day_sessions = [s for s in sessions if s.session_date == day]
        result.append(
            DayPlan(
                date=day,
                label=day.strftime("%a"),
                total_minutes=sum(s.duration_minutes for s in day_sessions),
                completed_minutes=sum(
                    (s.actual_minutes or s.duration_minutes)
                    for s in day_sessions
                    if s.status == "completed"
                ),
                sessions=[session_out(s) for s in day_sessions],
            )
        )
    return result


@router.get("/range", response_model=List[SessionOut], summary="Sessions in a date range")
def range_view(
    user: CurrentUser, db: DbSession, start: date, end: date
) -> List[SessionOut]:
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The end date must not be before the start date.",
        )
    if (end - start).days > 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please request a range of 400 days or fewer.",
        )
    return [session_out(s) for s in planner.sessions_between(db, user, start, end)]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@router.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a session manually",
)
def create_session(
    payload: SessionCreate, user: CurrentUser, db: DbSession
) -> SessionOut:
    if payload.subject_id is not None:
        subject = db.get(Subject, payload.subject_id)
        if subject is None or subject.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That subject does not belong to you.",
            )
    if payload.topic_id is not None:
        topic = db.get(Topic, payload.topic_id)
        if topic is None or topic.unit.subject.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That topic does not belong to you.",
            )

    active = planner.active_plan(db, user)
    session = StudySession(
        user_id=user.id, plan_id=active.id if active else None, **payload.model_dump()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.patch("/sessions/{session_id}", response_model=SessionOut, summary="Edit a session")
def update_session(
    session_id: int, payload: SessionUpdate, user: CurrentUser, db: DbSession
) -> SessionOut:
    session = _get_session(db, user, session_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(session, field, value)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionOut,
    summary="Mark a session complete",
    description=(
        "Awards XP, extends the study streak and optionally marks the linked "
        "topic complete (which also books its spaced-repetition revisions)."
    ),
)
def complete_session(
    session_id: int, payload: SessionComplete, user: CurrentUser, db: DbSession
) -> SessionOut:
    from app.services import revision as revision_service
    from app.models import CompletedTopic

    session = _get_session(db, user, session_id)
    if session.status == "completed":
        return session_out(session)

    session.status = "completed"
    session.actual_minutes = payload.actual_minutes or session.duration_minutes
    session.completed_at = utcnow()
    db.add(session)

    award_xp(db, user, 10 + session.duration_minutes // 30 * 5)
    touch_streak(db, user, session.session_date)
    log_activity(
        db, user, f"Completed “{session.title}”", kind="session", icon="circle-check"
    )

    if payload.mark_topic_complete and session.topic is not None:
        topic = session.topic
        if topic.status != "completed":
            topic.status = "completed"
            topic.confidence = payload.confidence
            topic.completed_at = utcnow()
            db.add(topic)
            db.add(
                CompletedTopic(
                    user_id=user.id,
                    topic_id=topic.id,
                    subject_id=topic.unit.subject_id,
                    completed_on=session.session_date,
                    minutes_spent=session.actual_minutes,
                    confidence=payload.confidence,
                )
            )
            award_xp(db, user, 20)
            revision_service.schedule_for_topic(
                db, user, topic, topic.unit.subject, session.session_date
            )

    db.commit()
    evaluate(db, user)
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.post(
    "/sessions/{session_id}/skip", response_model=SessionOut, summary="Skip a session"
)
def skip_session(session_id: int, user: CurrentUser, db: DbSession) -> SessionOut:
    session = _get_session(db, user, session_id)
    session.status = "skipped"
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.post(
    "/sessions/{session_id}/reset",
    response_model=SessionOut,
    summary="Return a session to pending",
)
def reset_session(session_id: int, user: CurrentUser, db: DbSession) -> SessionOut:
    session = _get_session(db, user, session_id)
    session.status = "pending"
    session.actual_minutes = 0
    session.completed_at = None
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@router.delete(
    "/sessions/{session_id}", response_model=Message, summary="Delete a session"
)
def delete_session(session_id: int, user: CurrentUser, db: DbSession) -> Message:
    session = _get_session(db, user, session_id)
    title = session.title
    db.delete(session)
    db.commit()
    return Message(message=f"“{title}” removed from your timetable.")
