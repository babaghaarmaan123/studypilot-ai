"""The AI study engine.

Given everything StudyPilot knows about a student — exam dates, available
hours, subject difficulty, remaining syllabus, admissions tests, completed
topics and weak subjects — this module produces a concrete, time-boxed
timetable.

The algorithm, in one paragraph: every active subject gets an *urgency score*
built from exam proximity, difficulty, student-set priority, weak-subject
status and how much syllabus is left. Those scores are normalised into target
shares of the student's available time. Each day is then filled block by block,
always giving the next block to whichever subject is furthest *behind* its
target share (largest-deficit allocation), which naturally interleaves subjects
instead of batching them. Revision entries that fall due, admissions-test
practice and past-paper sessions are reserved before general study time, so
fixed commitments never get squeezed out.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.catalog import ADMISSION_EXAM_INDEX, STUDY_WINDOW_START
from app.models import (
    Exam,
    RevisionPlan,
    StudyPlan,
    StudySession,
    Subject,
    Topic,
    User,
)
from app.services.serializers import load_json_list

# --- Tuning constants -------------------------------------------------------

#: Longest single block of work, per study habit. The student's shortest
#: applicable cap wins — someone who both procrastinates and loses focus gets
#: the 25 minute treatment.
HABIT_BLOCK_MINUTES: Dict[str, int] = {
    "procrastinate": 25,
    "focus": 40,
    "time_management": 45,
    "cram": 60,
    "regular": 65,
}
DEFAULT_BLOCK_MINUTES = 50
MIN_BLOCK_MINUTES = 20

PRIORITY_WEIGHT = {"low": 0.75, "medium": 1.0, "high": 1.35}

#: How hard an approaching exam pulls time towards a subject.
def _exam_pressure(days_until: Optional[int]) -> float:
    if days_until is None:
        return 0.85          # no exam booked yet
    if days_until < 0:
        return 0.4           # exam has passed
    if days_until <= 7:
        return 3.0
    if days_until <= 14:
        return 2.5
    if days_until <= 30:
        return 2.0
    if days_until <= 60:
        return 1.5
    if days_until <= 100:
        return 1.2
    return 1.0


@dataclass
class SubjectQueue:
    """A subject plus the topics still to be covered, in syllabus order."""

    subject: Subject
    topics: List[Topic]
    score: float
    target_share: float = 0.0
    allocated_minutes: int = 0
    cursor: int = 0
    minutes_into_topic: Dict[int, int] = field(default_factory=dict)

    @property
    def remaining_hours(self) -> float:
        return sum(t.estimated_hours for t in self.topics[self.cursor:])

    def current_topic(self) -> Optional[Topic]:
        if self.cursor < len(self.topics):
            return self.topics[self.cursor]
        return None

    def consume(self, minutes: int) -> Optional[Topic]:
        """Book `minutes` against the current topic, advancing when it's full."""
        topic = self.current_topic()
        self.allocated_minutes += minutes
        if topic is None:
            return None
        spent = self.minutes_into_topic.get(topic.id, 0) + minutes
        self.minutes_into_topic[topic.id] = spent
        if spent >= topic.estimated_hours * 60 - 5:
            self.cursor += 1
        return topic


# ---------------------------------------------------------------------------
# Capacity helpers
# ---------------------------------------------------------------------------
def block_minutes_for(user: User) -> int:
    habits = load_json_list(user.study_habits)
    caps = [HABIT_BLOCK_MINUTES[h] for h in habits if h in HABIT_BLOCK_MINUTES]
    return min(caps) if caps else DEFAULT_BLOCK_MINUTES


def break_minutes_for(block: int) -> int:
    return 10 if block <= 45 else 15


def daily_capacity_minutes(user: User, day: date) -> int:
    hours = user.weekend_hours if day.weekday() >= 5 else user.weekday_hours
    return int(round(hours * 60))


def _start_hour_for(user: User, total_minutes: int) -> int:
    base = STUDY_WINDOW_START.get(user.preferred_study_time, 17)
    # A long day cannot start at 20:00 — pull it earlier so it still fits.
    if total_minutes > 180:
        base = max(8, base - 2)
    if total_minutes > 300:
        base = max(8, base - 1)
    return base


def _time_string(hour: int, minute: int) -> str:
    hour = hour % 24
    return f"{hour:02d}:{minute:02d}"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _days_until_next_exam(subject: Subject, today: date) -> Optional[int]:
    upcoming = [e.exam_date for e in subject.exams if e.exam_date >= today]
    if not upcoming:
        return None
    return (min(upcoming) - today).days


def score_subject(subject: Subject, today: date) -> float:
    """Urgency score. Higher means "give this subject more time"."""
    pressure = _exam_pressure(_days_until_next_exam(subject, today))
    difficulty = 0.8 + subject.difficulty * 0.1          # 0.9 .. 1.3
    priority = PRIORITY_WEIGHT.get(subject.priority, 1.0)
    weak = 1.25 if subject.is_weak else 1.0
    confidence = 1.0 + (3 - subject.confidence) * 0.06   # low confidence -> more time

    remaining = max(0.0, 100.0 - subject.completion_percentage) / 100.0
    coverage = 0.7 + remaining * 0.6                     # 0.7 .. 1.3

    return round(pressure * difficulty * priority * weak * confidence * coverage, 4)


def build_queues(user: User, today: date) -> List[SubjectQueue]:
    queues: List[SubjectQueue] = []
    for subject in user.subjects:
        if subject.is_archived:
            continue
        pending = [
            topic
            for unit in subject.units
            for topic in unit.topics
            if topic.status != "completed"
        ]
        if not pending:
            continue
        queues.append(
            SubjectQueue(
                subject=subject, topics=pending, score=score_subject(subject, today)
            )
        )

    # Normalise scores weighted by how much work is genuinely left.
    weighted = [q.score * math.sqrt(max(q.remaining_hours, 0.5)) for q in queues]
    total = sum(weighted) or 1.0
    for queue, weight in zip(queues, weighted):
        queue.target_share = weight / total
    return queues


def _pick_queue(
    queues: List[SubjectQueue],
    allocated_total: int,
    block: int,
    seen_today: Optional[set] = None,
):
    """Largest-deficit choice: whoever is furthest below their target share.

    Topics already scheduled earlier the same day are deprioritised so a day
    covers several different things rather than grinding one topic six times.
    """
    candidates = [q for q in queues if q.current_topic() is not None]
    if not candidates:
        return None

    if seen_today:
        fresh = [q for q in candidates if q.current_topic().id not in seen_today]
        if fresh:
            candidates = fresh

    projected = allocated_total + block
    return max(
        candidates,
        key=lambda q: (q.target_share * projected) - q.allocated_minutes,
    )


# ---------------------------------------------------------------------------
# Fixed commitments
# ---------------------------------------------------------------------------
def _admission_weekdays(sessions_per_week: int) -> List[int]:
    """Spread N sessions evenly across the week (0 = Monday)."""
    count = max(1, min(7, sessions_per_week))
    return sorted({round(i * 7 / count) % 7 for i in range(count)})


def _exam_days(user: User, start: date, end: date) -> Dict[date, List[Exam]]:
    mapping: Dict[date, List[Exam]] = {}
    for exam in user.exams:
        if start <= exam.exam_date <= end:
            mapping.setdefault(exam.exam_date, []).append(exam)
    return mapping


def _past_paper_targets(user: User, today: date) -> List[Subject]:
    """Subjects close enough to an exam that timed papers are worth the hours."""
    scored: List[Tuple[int, Subject]] = []
    for subject in user.subjects:
        if subject.is_archived:
            continue
        days = _days_until_next_exam(subject, today)
        if days is not None and 0 <= days <= 45 and subject.completion_percentage >= 35:
            scored.append((days, subject))
    scored.sort(key=lambda pair: pair[0])
    return [subject for _, subject in scored[:2]]


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------
def generate_plan(
    db: Session,
    user: User,
    horizon_days: int = 28,
    start_date: Optional[date] = None,
    replace_existing: bool = True,
    regenerated_from: Optional[int] = None,
) -> StudyPlan:
    """Build and persist a fresh timetable for the next `horizon_days` days."""
    today = start_date or date.today()
    end = today + timedelta(days=horizon_days - 1)

    if replace_existing:
        _archive_existing(db, user, from_date=today)

    plan = StudyPlan(
        user_id=user.id,
        start_date=today,
        end_date=end,
        horizon_days=horizon_days,
        regenerated_from_id=regenerated_from,
        is_active=True,
    )
    db.add(plan)
    db.flush()

    queues = build_queues(user, today)
    block = block_minutes_for(user)
    exams_by_day = _exam_days(user, today, end)
    paper_subjects = _past_paper_targets(user, today)

    # Pending revisions that fall inside the horizon are fixed commitments.
    revisions = db.scalars(
        select(RevisionPlan)
        .where(
            RevisionPlan.user_id == user.id,
            RevisionPlan.status == "pending",
            RevisionPlan.scheduled_date <= end,
        )
        .order_by(RevisionPlan.scheduled_date)
    ).all()
    revisions_by_day: Dict[date, List[RevisionPlan]] = {}
    for revision in revisions:
        # Anything overdue is pulled to the front of the plan.
        day = max(revision.scheduled_date, today)
        revisions_by_day.setdefault(day, []).append(revision)

    # Admissions-test practice, spread across the week.
    admission_schedule: Dict[int, List[dict]] = {}
    for entry in user.admission_exams:
        meta = ADMISSION_EXAM_INDEX.get(entry.code)
        if not meta:
            continue
        for weekday in _admission_weekdays(int(meta.get("sessions_per_week", 1))):
            admission_schedule.setdefault(weekday, []).append(
                {
                    "code": entry.code,
                    "title": meta["practice_title"],
                    "minutes": int(meta.get("session_minutes", 60)),
                    "focus": meta["focus"],
                }
            )

    allocated_total = 0
    total_minutes = 0
    created: List[StudySession] = []
    #: How many blocks each topic has been given, so long topics can be
    #: labelled "part 2", "part 3" instead of repeating the same title.
    topic_parts: Dict[int, int] = {}

    for offset in range(horizon_days):
        day = today + timedelta(days=offset)
        capacity = daily_capacity_minutes(user, day)
        if capacity < MIN_BLOCK_MINUTES:
            continue

        day_blocks: List[dict] = []

        # 1. Exam day — a short final review, nothing else.
        if day in exams_by_day:
            for exam in exams_by_day[day]:
                day_blocks.append(
                    {
                        "title": f"Final review — {exam.title}",
                        "description": (
                            f"Light recap before your {exam.exam_time or '09:00'} exam. "
                            "Formulae, definitions and past mistakes only."
                        ),
                        "minutes": 30,
                        "kind": "revision",
                        "subject_id": exam.subject_id,
                        "topic_id": None,
                        "score": 5.0,
                    }
                )
            _persist_day(db, plan, user, day, day_blocks, created)
            total_minutes += sum(b["minutes"] for b in day_blocks)
            continue

        remaining = capacity

        # 2. Spaced-repetition revisions due today.
        for revision in revisions_by_day.get(day, []):
            minutes = min(revision.duration_minutes, remaining)
            if minutes < 15:
                break
            day_blocks.append(
                {
                    "title": f"Revision — {revision.topic.name}",
                    "description": (
                        f"Spaced repetition ({revision.interval_label}) for "
                        f"{revision.subject.name}. Recall first, then check."
                    ),
                    "minutes": minutes,
                    "kind": "revision",
                    "subject_id": revision.subject_id,
                    "topic_id": revision.topic_id,
                    "score": 4.0,
                }
            )
            remaining -= minutes

        # 3. Admissions-test practice.
        for entry in admission_schedule.get(day.weekday(), []):
            minutes = min(entry["minutes"], remaining)
            if minutes < 30:
                break
            day_blocks.append(
                {
                    "title": entry["title"],
                    "description": f"{entry['code']} preparation · {entry['focus']}.",
                    "minutes": minutes,
                    "kind": "admission",
                    "subject_id": None,
                    "topic_id": None,
                    "score": 4.5,
                }
            )
            remaining -= minutes

        # 4. One timed past paper on Saturdays when exams are close.
        if day.weekday() == 5 and paper_subjects and remaining >= 90:
            subject = paper_subjects[(offset // 7) % len(paper_subjects)]
            day_blocks.append(
                {
                    "title": f"Past paper — {subject.name}",
                    "description": "Full paper under timed conditions, then mark it "
                    "against the mark scheme and log your score.",
                    "minutes": 90,
                    "kind": "past_paper",
                    "subject_id": subject.id,
                    "topic_id": None,
                    "score": 3.5,
                }
            )
            remaining -= 90

        # 5. Fill what is left with syllabus study, largest deficit first.
        seen_today: set = set()
        while remaining >= MIN_BLOCK_MINUTES and queues:
            size = min(block, remaining)
            queue = _pick_queue(queues, allocated_total, size, seen_today)
            if queue is None:
                break
            topic = queue.current_topic()
            queue.consume(size)
            allocated_total += size
            seen_today.add(topic.id)

            part = topic_parts.get(topic.id, 0) + 1
            topic_parts[topic.id] = part
            suffix = f" (part {part})" if part > 1 else ""

            day_blocks.append(
                {
                    "title": f"{queue.subject.name} — {topic.name}{suffix}",
                    "description": _study_description(queue.subject, topic, part),
                    "minutes": size,
                    "kind": "study",
                    "subject_id": queue.subject.id,
                    "topic_id": topic.id,
                    "score": queue.score,
                }
            )
            remaining -= size

        total_minutes += sum(b["minutes"] for b in day_blocks)
        _persist_day(db, plan, user, day, day_blocks, created)

    plan.total_hours = round(total_minutes / 60, 1)
    plan.strategy = _strategy_text(user, queues, today, end)
    plan.focus_notes = json.dumps(_focus_notes(user, queues, today))
    db.add(plan)
    db.flush()
    return plan


def _study_description(subject: Subject, topic: Topic, part: int = 1) -> str:
    if part > 1:
        return (
            f"{subject.name} · {topic.name}. Continuing from your last block — "
            "start by recapping what you covered, then push further."
        )
    difficulty_note = {
        1: "Quick pass — this one should be comfortable.",
        2: "Work through the notes, then a few questions.",
        3: "Notes first, then exam-style questions.",
        4: "Take it slowly: worked examples before you attempt questions.",
        5: "Hardest tier — break it into two passes and revisit tomorrow.",
    }[max(1, min(5, topic.difficulty))]
    return f"{subject.name} · {topic.name}. {difficulty_note}"


def _persist_day(
    db: Session,
    plan: StudyPlan,
    user: User,
    day: date,
    blocks: List[dict],
    created: List[StudySession],
) -> None:
    """Lay the day's blocks out on a clock and write them to the database."""
    if not blocks:
        return

    total = sum(b["minutes"] for b in blocks)
    hour = _start_hour_for(user, total)
    minute = 0
    gap = break_minutes_for(max(b["minutes"] for b in blocks))

    for index, item in enumerate(blocks):
        session = StudySession(
            user_id=user.id,
            plan_id=plan.id,
            subject_id=item["subject_id"],
            topic_id=item["topic_id"],
            title=item["title"],
            description=item["description"],
            session_date=day,
            start_time=_time_string(hour, minute),
            duration_minutes=item["minutes"],
            kind=item["kind"],
            status="pending",
            priority_score=round(float(item["score"]), 3),
        )
        db.add(session)
        created.append(session)

        advance = item["minutes"] + (gap if index < len(blocks) - 1 else 0)
        minute += advance
        hour += minute // 60
        minute %= 60


def _archive_existing(db: Session, user: User, from_date: date) -> None:
    """Retire current plans and clear their untouched future sessions.

    Completed and missed sessions are kept — they are the student's history and
    analytics depends on them.
    """
    stale = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.session_date >= from_date,
            StudySession.status == "pending",
        )
    ).all()
    for session in stale:
        db.delete(session)

    plans = db.scalars(
        select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.is_active)
    ).all()
    for plan in plans:
        plan.is_active = False
        db.add(plan)
    db.flush()


def _strategy_text(
    user: User, queues: List[SubjectQueue], start: date, end: date
) -> str:
    if not queues:
        return (
            "You have no outstanding syllabus topics. Add subjects or reopen "
            "topics you would like to revisit and regenerate the plan."
        )

    ranked = sorted(queues, key=lambda q: q.target_share, reverse=True)
    top = ", ".join(q.subject.name for q in ranked[:3])
    weekly = round((user.weekday_hours * 5 + user.weekend_hours * 2), 1)
    admissions = [entry.code for entry in user.admission_exams]

    parts = [
        f"Plan covering {start.strftime('%d %b')} to {end.strftime('%d %b')} at "
        f"roughly {weekly} hours a week.",
        f"Most time goes to {top}, weighted by exam dates, difficulty and how "
        "much syllabus you have left.",
    ]
    if admissions:
        parts.append(
            "Admissions preparation for "
            + ", ".join(admissions)
            + " is booked in weekly so it never competes with school revision."
        )
    parts.append(
        "Spaced-repetition revisions are placed first each day, so recall work "
        "is protected even on busy days."
    )
    return " ".join(parts)


def _focus_notes(user: User, queues: List[SubjectQueue], today: date) -> List[str]:
    notes: List[str] = []
    ranked = sorted(queues, key=lambda q: q.score, reverse=True)

    for queue in ranked[:3]:
        days = _days_until_next_exam(queue.subject, today)
        when = f"{days} days to the exam" if days is not None else "no exam booked yet"
        notes.append(
            f"{queue.subject.name}: {queue.subject.completion_percentage:.0f}% covered, "
            f"{queue.remaining_hours:.0f}h left, {when}."
        )

    weak = [q.subject.name for q in queues if q.subject.is_weak]
    if weak:
        notes.append("Extra time reserved for weaker subjects: " + ", ".join(weak) + ".")

    habits = load_json_list(user.study_habits)
    if "focus" in habits or "procrastinate" in habits:
        notes.append(
            f"Blocks capped at {block_minutes_for(user)} minutes with breaks between "
            "them, based on the study habits you described."
        )
    if "cram" in habits:
        notes.append(
            "Revision checkpoints start earlier than usual to break the "
            "study-only-before-exams pattern."
        )
    return notes


# ---------------------------------------------------------------------------
# Missed work / automatic regeneration
# ---------------------------------------------------------------------------
def mark_missed_sessions(db: Session, user: User, today: Optional[date] = None) -> int:
    """Flip yesterday-and-earlier pending sessions to `missed`."""
    today = today or date.today()
    stale = db.scalars(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.session_date < today,
            StudySession.status == "pending",
        )
    ).all()
    for session in stale:
        session.status = "missed"
        db.add(session)

    overdue = db.scalars(
        select(RevisionPlan).where(
            RevisionPlan.user_id == user.id,
            RevisionPlan.scheduled_date < today - timedelta(days=2),
            RevisionPlan.status == "pending",
        )
    ).all()
    for revision in overdue:
        revision.status = "missed"
        db.add(revision)

    if stale or overdue:
        db.flush()
    return len(stale)


def regenerate_after_missed(
    db: Session, user: User, threshold: int = 3
) -> Tuple[Optional[StudyPlan], int]:
    """Rebuild the timetable when the student has fallen behind.

    Returns (plan_or_none, missed_count). A plan is only regenerated once the
    number of missed sessions crosses `threshold`, so one bad evening does not
    reshuffle everything.
    """
    missed = mark_missed_sessions(db, user)
    if missed < threshold:
        return None, missed

    active = db.scalars(
        select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.is_active)
    ).first()
    horizon = active.horizon_days if active else 28
    plan = generate_plan(
        db,
        user,
        horizon_days=horizon,
        replace_existing=True,
        regenerated_from=active.id if active else None,
    )
    return plan, missed


def active_plan(db: Session, user: User) -> Optional[StudyPlan]:
    return db.scalars(
        select(StudyPlan)
        .where(StudyPlan.user_id == user.id, StudyPlan.is_active)
        .order_by(StudyPlan.created_at.desc())
    ).first()


def sessions_between(
    db: Session, user: User, start: date, end: date
) -> List[StudySession]:
    return list(
        db.scalars(
            select(StudySession)
            .where(
                StudySession.user_id == user.id,
                StudySession.session_date >= start,
                StudySession.session_date <= end,
            )
            .order_by(StudySession.session_date, StudySession.start_time)
        ).all()
    )


def recalculate_exam_readiness(db: Session, user: User) -> None:
    """Preparation % per exam = syllabus coverage, adjusted by past papers."""
    today = date.today()
    for exam in user.exams:
        if exam.subject is None:
            continue
        coverage = exam.subject.completion_percentage
        papers = [p for p in exam.subject.past_papers if p.scored]
        if papers:
            recent = sorted(papers, key=lambda p: p.date_taken)[-3:]
            average = sum(p.percentage for p in recent) / len(recent)
            coverage = coverage * 0.6 + average * 0.4
        exam.preparation_percentage = round(min(100.0, max(0.0, coverage)), 1)
        db.add(exam)

    for entry in user.admission_exams:
        sessions = db.scalars(
            select(StudySession).where(
                StudySession.user_id == user.id,
                StudySession.kind == "admission",
                StudySession.status == "completed",
            )
        ).all()
        done = len(sessions)
        # 20 completed practice sessions is treated as fully prepared.
        entry.preparation_percentage = round(min(100.0, done / 20 * 100), 1)
        db.add(entry)
    db.flush()
