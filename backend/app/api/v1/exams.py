"""Exam timetable and countdowns."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.models import AdmissionExam, Exam, Subject
from app.schemas.academic import ExamCreate, ExamOut, ExamUpdate
from app.schemas.common import Message
from app.schemas.progress import ExamCountdownList
from app.services.activity import log_activity
from app.services.planner import recalculate_exam_readiness
from app.services.serializers import exam_countdown, exam_out

router = APIRouter(prefix="/exams", tags=["Exams"])


def _get_exam(db, user, exam_id: int) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None or exam.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found."
        )
    return exam


def _validate_subject(db, user, subject_id: Optional[int]) -> None:
    if subject_id is None:
        return
    subject = db.get(Subject, subject_id)
    if subject is None or subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That subject does not belong to you.",
        )


@router.get("", response_model=List[ExamOut], summary="List exams")
def list_exams(
    user: CurrentUser,
    db: DbSession,
    upcoming_only: bool = Query(False, description="Hide exams already sat"),
    kind: Optional[str] = Query(None, pattern="^(school|admission)$"),
) -> List[ExamOut]:
    recalculate_exam_readiness(db, user)
    db.commit()

    today = date.today()
    exams = [e for e in user.exams if not upcoming_only or e.exam_date >= today]
    if kind:
        exams = [e for e in exams if e.kind == kind]
    exams.sort(key=lambda e: (e.exam_date, e.exam_time or ""))
    return [exam_out(e) for e in exams]


@router.get(
    "/countdown",
    response_model=ExamCountdownList,
    summary="Countdowns split by school and admissions exams",
)
def countdowns(user: CurrentUser, db: DbSession) -> ExamCountdownList:
    recalculate_exam_readiness(db, user)
    db.commit()

    today = date.today()
    upcoming = sorted(
        (e for e in user.exams if e.exam_date >= today), key=lambda e: e.exam_date
    )
    return ExamCountdownList(
        school=[exam_countdown(e) for e in upcoming if e.kind == "school"],
        admission=[exam_countdown(e) for e in upcoming if e.kind == "admission"],
    )


@router.post(
    "",
    response_model=ExamOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exam",
)
def create_exam(payload: ExamCreate, user: CurrentUser, db: DbSession) -> ExamOut:
    _validate_subject(db, user, payload.subject_id)
    exam = Exam(user_id=user.id, **payload.model_dump())
    db.add(exam)
    log_activity(
        db, user, f"Added exam: {exam.title}", kind="exam", icon="calendar-clock"
    )
    db.commit()
    db.refresh(exam)
    return exam_out(exam)


@router.patch("/{exam_id}", response_model=ExamOut, summary="Edit an exam")
def update_exam(
    exam_id: int, payload: ExamUpdate, user: CurrentUser, db: DbSession
) -> ExamOut:
    exam = _get_exam(db, user, exam_id)
    data = payload.model_dump(exclude_unset=True)
    if "subject_id" in data:
        _validate_subject(db, user, data["subject_id"])
    for field, value in data.items():
        setattr(exam, field, value)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam_out(exam)


@router.delete("/{exam_id}", response_model=Message, summary="Delete an exam")
def delete_exam(exam_id: int, user: CurrentUser, db: DbSession) -> Message:
    exam = _get_exam(db, user, exam_id)
    title = exam.title
    db.delete(exam)
    db.commit()
    return Message(message=f"{title} removed from your timetable.")


# ---------------------------------------------------------------------------
# Admissions tests the student is preparing for
# ---------------------------------------------------------------------------
@router.patch(
    "/admission/{admission_id}",
    summary="Set the date for an admissions test",
    description="Adds the sitting date so the dashboard can count down to it.",
)
def set_admission_date(
    admission_id: int, exam_date: date, user: CurrentUser, db: DbSession
) -> dict:
    entry = db.get(AdmissionExam, admission_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admissions test not found."
        )
    entry.exam_date = exam_date
    db.add(entry)

    # Mirror it onto the exam timetable so it shows in the calendar too.
    existing = next(
        (e for e in user.exams if e.kind == "admission" and e.title == entry.name), None
    )
    if existing:
        existing.exam_date = exam_date
        db.add(existing)
    else:
        db.add(
            Exam(
                user_id=user.id,
                title=entry.name,
                exam_date=exam_date,
                exam_time="09:00",
                kind="admission",
            )
        )
    db.commit()
    return {
        "ok": True,
        "id": entry.id,
        "code": entry.code,
        "exam_date": exam_date.isoformat(),
    }
