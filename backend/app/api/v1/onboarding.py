"""The AI onboarding assistant."""

import json

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.data.catalog import catalog_payload
from app.schemas.onboarding import (
    MentorSummary,
    OnboardingDraft,
    OnboardingDraftOut,
    OnboardingSubmit,
)
from app.services import mentor
from app.services import onboarding as onboarding_service
from app.services.planner import active_plan

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get(
    "/questions",
    summary="Question definitions and answer options",
    description=(
        "Everything the wizard needs to render its 10 questions, including the "
        "subject lists per curriculum, admissions tests, universities and degrees. "
        "Serving this from the API keeps the options in one place."
    ),
)
def questions() -> dict:
    catalog = catalog_payload()
    return {
        "intro": {
            "title": "Hi! I'm your AI Study Mentor.",
            "subtitle": (
                "I'm going to ask a few questions to create your personalised "
                "study plan."
            ),
            "question_count": 10,
            "estimated_minutes": 3,
        },
        "catalog": catalog,
        "questions": [
            {"id": 1, "key": "name", "type": "text",
             "title": "What is your name?",
             "help": "This is how I'll greet you on your dashboard."},
            {"id": 2, "key": "year_group", "type": "single",
             "title": "Which Year Group are you currently in?",
             "options": catalog["year_groups"]},
            {"id": 3, "key": "curriculum", "type": "single",
             "title": "Which curriculum are you studying?",
             "options": catalog["curricula"]},
            {"id": 4, "key": "subjects", "type": "multi_dynamic",
             "title": "Which subjects are you studying?",
             "depends_on": "curriculum",
             "help": "Pick everything you're sitting — I'll build a syllabus for each."},
            {"id": 5, "key": "admission_exams", "type": "conditional_multi",
             "title": "Are you preparing for any university admission exams?",
             "options": catalog["admission_exams"]},
            {"id": 6, "key": "universities", "type": "multi",
             "title": "Which universities are you interested in?",
             "options": catalog["universities"]},
            {"id": 7, "key": "target_degree", "type": "single",
             "title": "Which degree do you plan to study?",
             "options": catalog["degrees"]},
            {"id": 8, "key": "exams", "type": "exam_table",
             "title": "Enter your exam timetable.",
             "help": "Add each paper with its board, date and time. You can skip "
                     "this and add exams later."},
            {"id": 9, "key": "study_hours", "type": "hours",
             "title": "How many hours can you study?",
             "options": catalog["preferred_study_times"]},
            {"id": 10, "key": "study_habits", "type": "multi",
             "title": "How would you describe your study habits?",
             "options": catalog["study_habits"]},
        ],
    }


@router.get(
    "/draft",
    response_model=OnboardingDraftOut,
    summary="Read the autosaved answers",
    description="Lets a student close the tab mid-wizard and pick up where they left off.",
)
def get_draft(user: CurrentUser) -> OnboardingDraftOut:
    answers = {}
    if user.onboarding_draft:
        try:
            answers = json.loads(user.onboarding_draft) or {}
        except ValueError:
            answers = {}
    return OnboardingDraftOut(
        step=user.onboarding_step,
        answers=answers,
        completed=user.onboarding_completed,
    )


@router.put(
    "/draft",
    response_model=OnboardingDraftOut,
    summary="Autosave answers",
    description="Called by the wizard after every answer so nothing is ever lost.",
)
def save_draft(
    payload: OnboardingDraft, user: CurrentUser, db: DbSession
) -> OnboardingDraftOut:
    user.onboarding_step = payload.step
    user.onboarding_draft = json.dumps(payload.answers)
    db.add(user)
    db.commit()
    return OnboardingDraftOut(
        step=user.onboarding_step,
        answers=payload.answers,
        completed=user.onboarding_completed,
    )


@router.post(
    "/complete",
    response_model=MentorSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Submit onboarding and generate the first plan",
    description=(
        "Creates the student's subjects with seeded syllabi, records their exam "
        "timetable, universities and admissions tests, detects weak subjects, "
        "generates a 28-day study plan and returns the AI Academic Mentor summary."
    ),
)
def complete(
    payload: OnboardingSubmit, user: CurrentUser, db: DbSession
) -> MentorSummary:
    return onboarding_service.apply(db, user, payload)


@router.get(
    "/summary",
    response_model=MentorSummary,
    summary="Re-read the AI Academic Mentor summary",
)
def summary(user: CurrentUser, db: DbSession) -> MentorSummary:
    plan = active_plan(db, user)
    headline, text, focus = mentor.build_summary(db, user, plan)
    return MentorSummary(
        headline=headline,
        summary=text,
        focus_points=focus,
        plan_id=plan.id if plan else None,
        subjects_created=len([s for s in user.subjects if not s.is_archived]),
        topics_created=sum(len(s.topics) for s in user.subjects),
        sessions_created=len(plan.sessions) if plan else 0,
        revisions_created=len(user.revisions),
    )
