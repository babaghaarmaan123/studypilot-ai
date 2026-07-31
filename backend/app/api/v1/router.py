"""Mounts every v1 router."""

from fastapi import APIRouter

from app.api.v1 import (
    achievements,
    analytics,
    auth,
    catalog,
    exams,
    notifications,
    onboarding,
    past_papers,
    plans,
    revision,
    subjects,
    tasks,
    users,
)

api_router = APIRouter()

api_router.include_router(catalog.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(onboarding.router)
api_router.include_router(subjects.router)
api_router.include_router(exams.router)
api_router.include_router(plans.router)
api_router.include_router(revision.router)
api_router.include_router(past_papers.router)
api_router.include_router(achievements.router)
api_router.include_router(analytics.router)
api_router.include_router(notifications.router)
api_router.include_router(tasks.router)
