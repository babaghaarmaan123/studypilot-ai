"""Turns the 10 onboarding answers into a fully populated account."""

import json
from typing import Dict, List

from sqlalchemy.orm import Session

from app.data.catalog import ADMISSION_EXAM_INDEX
from app.models import AdmissionExam, Exam, Subject, TargetUniversity, User
from app.schemas.onboarding import MentorSummary, OnboardingSubmit
from app.services import mentor, planner, subjects as subject_service
from app.services.achievements import ensure_achievements, evaluate
from app.services.activity import log_activity, notify


def apply(db: Session, user: User, payload: OnboardingSubmit) -> MentorSummary:
    # --- Q1, Q2, Q3, Q7, Q9, Q10 -> profile --------------------------------
    user.name = payload.name.strip()
    user.year_group = payload.year_group
    user.curriculum = payload.curriculum
    user.target_degree = payload.target_degree
    user.weekday_hours = payload.weekday_hours
    user.weekend_hours = payload.weekend_hours
    user.preferred_study_time = payload.preferred_study_time
    user.study_habits = json.dumps(payload.study_habits)
    db.add(user)

    # Onboarding is re-runnable. Reassigning these collections lets the
    # delete-orphan cascade clear the previous answers for us.
    # --- Q6 -> universities -------------------------------------------------
    user.universities = [
        TargetUniversity(name=name) for name in dict.fromkeys(payload.universities)
    ]

    # --- Q5 -> admissions tests --------------------------------------------
    admissions = []
    if payload.preparing_admission_exams:
        for code in dict.fromkeys(payload.admission_exams):
            meta = ADMISSION_EXAM_INDEX.get(code)
            admissions.append(
                AdmissionExam(code=code, name=meta["name"] if meta else code)
            )
    user.admission_exams = admissions
    db.flush()

    # --- Q4 -> subjects (+ seeded syllabus) --------------------------------
    existing = {s.name.lower(): s for s in user.subjects}
    created_subjects: List[Subject] = []
    topics_created = 0

    for index, name in enumerate(payload.subjects):
        if name.lower() in existing:
            created_subjects.append(existing[name.lower()])
            continue
        subject = subject_service.create_subject(
            db, user, name, curriculum=payload.curriculum, index_hint=index
        )
        created_subjects.append(subject)
        topics_created += len(subject.topics)
    db.flush()

    subject_lookup: Dict[str, Subject] = {s.name.lower(): s for s in created_subjects}

    # --- Q8 -> exam timetable ----------------------------------------------
    # Onboarding is re-runnable, and the wizard is pre-filled with the current
    # timetable, so what the student submits replaces it. Without clearing
    # first, a second pass duplicates every paper. Admissions-test dates live
    # in `kind="admission"` rows and are left alone.
    for stale in [exam for exam in user.exams if exam.kind == "school"]:
        db.delete(stale)
    db.flush()

    for entry in payload.exams:
        subject = subject_lookup.get(entry.subject.strip().lower())
        db.add(
            Exam(
                user_id=user.id,
                subject_id=subject.id if subject else None,
                title=(
                    f"{entry.subject} {entry.paper}".strip()
                    if entry.paper
                    else entry.subject
                ),
                exam_board=entry.exam_board,
                exam_date=entry.exam_date,
                exam_time=entry.exam_time,
                paper=entry.paper,
                kind="school",
            )
        )
        if subject and entry.exam_board and not subject.exam_board:
            subject.exam_board = entry.exam_board
            db.add(subject)
    db.flush()
    db.refresh(user)

    # --- Weak-subject detection then plan generation -----------------------
    subject_service.recalculate_weak_subjects(db, user)
    db.flush()

    plan = planner.generate_plan(db, user, horizon_days=28)
    planner.recalculate_exam_readiness(db, user)

    session_count = len(plan.sessions)
    revision_count = len(user.revisions)

    headline, summary, focus = mentor.build_summary(db, user, plan)
    user.mentor_summary = summary
    user.onboarding_completed = True
    user.onboarding_step = 10
    user.onboarding_draft = None
    db.add(user)

    ensure_achievements(db, user)
    log_activity(
        db,
        user,
        f"Completed onboarding — {len(created_subjects)} subjects and a "
        f"{plan.horizon_days}-day plan created",
        kind="onboarding",
        icon="sparkles",
    )
    notify(
        db,
        user,
        title="Your study plan is ready",
        message=summary[:180],
        kind="success",
        link="/app/dashboard",
    )
    db.commit()
    evaluate(db, user)
    db.commit()

    return MentorSummary(
        headline=headline,
        summary=summary,
        focus_points=focus,
        plan_id=plan.id,
        subjects_created=len(created_subjects),
        topics_created=topics_created,
        sessions_created=session_count,
        revisions_created=revision_count,
    )
