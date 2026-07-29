"""The AI Academic Mentor.

Turns the student's profile plus the generated plan into the narrative summary
shown at the end of onboarding and on the dashboard. Everything is derived
from the student's own data — there is no external model call, so the summary
is instant, free and completely private.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.data.catalog import ADMISSION_EXAM_INDEX, STUDY_HABITS
from app.models import StudyPlan, User
from app.services.serializers import load_json_list

_CURRICULUM_LABEL = {
    "gcse": "GCSE",
    "a_level": "A Levels",
    "international_a_level": "International A Levels",
}

_HABIT_STRATEGY = {h["code"]: h["strategy"] for h in STUDY_HABITS}


def _list_phrase(items: List[str], limit: int = 3) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    shown = items[:limit]
    extra = len(items) - len(shown)
    if len(shown) == 1:
        phrase = shown[0]
    else:
        phrase = ", ".join(shown[:-1]) + " and " + shown[-1]
    if extra > 0:
        phrase += f" (+{extra} more)"
    return phrase


def build_summary(
    db: Session, user: User, plan: Optional[StudyPlan] = None
) -> tuple[str, str, List[str]]:
    """Return (headline, summary paragraph, focus bullet points)."""
    today = date.today()
    curriculum = _CURRICULUM_LABEL.get(user.curriculum or "", "your course")
    subjects = [s.name for s in user.subjects if not s.is_archived]
    universities = [u.name for u in user.universities]
    admissions = [e.code for e in user.admission_exams]

    # --- Headline ----------------------------------------------------------
    first_name = (user.name or "there").split()[0]
    headline = f"Your plan is ready, {first_name}."

    # --- Summary paragraph -------------------------------------------------
    opening = f"Based on your {user.year_group or 'current year'} {curriculum}"
    if subjects:
        opening += f" in {_list_phrase(subjects, 4)}"

    goal_bits = []
    if admissions:
        goal_bits.append(f"your {_list_phrase(admissions, 3)} preparation")
    if user.target_degree and universities:
        goal_bits.append(
            f"your goal of studying {user.target_degree} at "
            f"{_list_phrase(universities, 2)}"
        )
    elif user.target_degree:
        goal_bits.append(f"your goal of studying {user.target_degree}")
    elif universities:
        goal_bits.append(f"your interest in {_list_phrase(universities, 2)}")

    if goal_bits:
        opening += ", " + " and ".join(goal_bits)

    weekly = round(user.weekday_hours * 5 + user.weekend_hours * 2, 1)
    summary = (
        f"{opening}, I have created a personalised study plan that balances school "
        f"revision with admissions preparation across about {weekly} hours a week, "
        f"scheduled in the {user.preferred_study_time}."
    )

    upcoming = sorted(
        (e for e in user.exams if e.exam_date >= today), key=lambda e: e.exam_date
    )
    if upcoming:
        nearest = upcoming[0]
        days = (nearest.exam_date - today).days
        summary += (
            f" Your next exam is {nearest.title} in {days} day"
            f"{'s' if days != 1 else ''}, so it takes priority in the schedule."
        )

    # --- Focus points ------------------------------------------------------
    focus: List[str] = []

    weak = [s.name for s in user.subjects if s.is_weak and not s.is_archived]
    if weak:
        focus.append(
            f"Extra time is reserved for {_list_phrase(weak)}, which look like your "
            "weakest areas right now."
        )

    if admissions:
        for code in admissions[:3]:
            meta = ADMISSION_EXAM_INDEX.get(code)
            if meta:
                per_week = meta.get("sessions_per_week", 1)
                focus.append(
                    f"{code}: {per_week} session{'s' if per_week != 1 else ''} a week "
                    f"on {meta['focus'].lower()}."
                )

    for habit in load_json_list(user.study_habits)[:2]:
        strategy = _HABIT_STRATEGY.get(habit)
        if strategy:
            focus.append(strategy)

    focus.append(
        "Every topic you complete is automatically revisited after 2, 7 and 14 days, "
        "with a final pass three days before the exam."
    )

    if plan is not None:
        focus.append(
            f"The plan covers {plan.horizon_days} days and "
            f"{plan.total_hours:.0f} hours of scheduled work. Regenerate it any time "
            "your timetable changes."
        )

    return headline, summary, focus


def refresh_summary(db: Session, user: User, plan: Optional[StudyPlan] = None) -> str:
    _, summary, _ = build_summary(db, user, plan)
    user.mentor_summary = summary
    db.add(user)
    db.flush()
    return summary
