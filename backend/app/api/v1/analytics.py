"""Dashboard and analytics endpoints."""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.progress import AnalyticsOut, DashboardOut
from app.services import analytics as analytics_service
from app.services import dashboard as dashboard_service

router = APIRouter(tags=["Dashboard & analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="Everything the dashboard needs in one call",
    description=(
        "Greeting, streak, today's goal and tasks, hours remaining, overall "
        "progress, upcoming exams, admissions countdowns, weak subjects and "
        "recent activity. Also runs the housekeeping pass that flags overdue "
        "sessions as missed and recalculates exam readiness."
    ),
)
def dashboard(user: CurrentUser, db: DbSession) -> DashboardOut:
    return dashboard_service.build(db, user)


@router.get(
    "/analytics",
    response_model=AnalyticsOut,
    summary="Study analytics",
    description=(
        "Weekly and monthly hours, subject distribution, completion per subject, "
        "a 12-week streak heatmap, revision progress, exam readiness, admissions "
        "readiness and the past-paper trend."
    ),
)
def analytics(user: CurrentUser, db: DbSession) -> AnalyticsOut:
    return AnalyticsOut(**analytics_service.build(db, user))
