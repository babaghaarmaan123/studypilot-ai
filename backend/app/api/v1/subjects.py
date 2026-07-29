"""Subject management and the syllabus tree (units + topics)."""

import secrets
from datetime import date
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.core.config import settings as app_settings
from app.core.deps import CurrentUser, DbSession
from app.db.base import utcnow
from app.models import CompletedTopic, Subject, Topic, Unit
from app.schemas.academic import (
    SubjectCreate,
    SubjectDetail,
    SubjectOut,
    SubjectUpdate,
    TopicComplete,
    TopicCreate,
    TopicOut,
    TopicUpdate,
    UnitCreate,
    UnitOut,
    UnitUpdate,
)
from app.schemas.common import Message
from app.services import revision as revision_service
from app.services import subjects as subject_service
from app.services import syllabus_parser
from app.services.achievements import evaluate
from app.services.activity import award_xp, log_activity, touch_streak
from app.services.serializers import subject_detail, subject_out, topic_out, unit_out

router = APIRouter(prefix="/subjects", tags=["Subjects & syllabus"])


# ---------------------------------------------------------------------------
# Lookup helpers — every one of these enforces ownership.
# ---------------------------------------------------------------------------
def _get_subject(db, user, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None or subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found."
        )
    return subject


def _get_unit(db, user, unit_id: int) -> Unit:
    unit = db.get(Unit, unit_id)
    if unit is None or unit.subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found."
        )
    return unit


def _get_topic(db, user, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None or topic.unit.subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found."
        )
    return topic


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------
@router.get("", response_model=List[SubjectOut], summary="List subjects")
def list_subjects(
    user: CurrentUser,
    include_archived: bool = Query(False, description="Include archived subjects"),
) -> List[SubjectOut]:
    subjects = [
        s for s in user.subjects if include_archived or not s.is_archived
    ]
    subjects.sort(key=lambda s: s.name.lower())
    return [subject_out(s) for s in subjects]


@router.post(
    "",
    response_model=SubjectDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Add a subject",
    description=(
        "Creates a subject. With `seed_syllabus` (the default) StudyPilot fills in "
        "a starter unit/topic breakdown for the subject so the planner has "
        "something to schedule immediately."
    ),
)
def create_subject(
    payload: SubjectCreate, user: CurrentUser, db: DbSession
) -> SubjectDetail:
    if any(
        s.name.lower() == payload.name.strip().lower() and not s.is_archived
        for s in user.subjects
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a subject called {payload.name}.",
        )

    subject = subject_service.create_subject(
        db,
        user,
        payload.name,
        curriculum=payload.curriculum,
        exam_board=payload.exam_board,
        colour=payload.colour,
        difficulty=payload.difficulty,
        priority=payload.priority,
        estimated_hours=payload.estimated_hours,
        target_grade=payload.target_grade,
        confidence=payload.confidence,
        index_hint=len(user.subjects),
        seed=payload.seed_syllabus,
    )
    log_activity(db, user, f"Added {subject.name}", kind="subject", icon="book-open")
    db.commit()
    db.refresh(subject)
    evaluate(db, user)
    db.commit()
    return subject_detail(subject)


@router.get("/{subject_id}", response_model=SubjectDetail, summary="Subject with syllabus")
def get_subject(subject_id: int, user: CurrentUser, db: DbSession) -> SubjectDetail:
    return subject_detail(_get_subject(db, user, subject_id))


@router.patch("/{subject_id}", response_model=SubjectDetail, summary="Edit a subject")
def update_subject(
    subject_id: int, payload: SubjectUpdate, user: CurrentUser, db: DbSession
) -> SubjectDetail:
    subject = _get_subject(db, user, subject_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(subject, field, value)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject_detail(subject)


@router.delete("/{subject_id}", response_model=Message, summary="Delete a subject")
def delete_subject(subject_id: int, user: CurrentUser, db: DbSession) -> Message:
    subject = _get_subject(db, user, subject_id)
    name = subject.name
    db.delete(subject)
    log_activity(db, user, f"Deleted {name}", kind="subject", icon="trash-2")
    db.commit()
    return Message(message=f"{name} deleted.")


@router.post(
    "/{subject_id}/seed-syllabus",
    response_model=SubjectDetail,
    summary="Fill an empty subject with its template syllabus",
    description=(
        "Legacy fallback that seeds a generic starter syllabus without a PDF. "
        "The primary flow is now `POST /{subject_id}/syllabus-pdf`."
    ),
)
def seed_syllabus(subject_id: int, user: CurrentUser, db: DbSession) -> SubjectDetail:
    subject = _get_subject(db, user, subject_id)
    if subject.units:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This subject already has a syllabus. Delete its units first.",
        )
    subject_service.seed_syllabus(db, subject)
    subject.syllabus_status = "ready"
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject_detail(subject)


@router.post(
    "/{subject_id}/syllabus-pdf",
    response_model=SubjectDetail,
    summary="Upload a syllabus specification PDF",
    description=(
        "Uploads the official exam board specification and generates the unit "
        "and topic breakdown from it automatically, including the content "
        "statements (key points) the board sets for each topic. Uploading "
        "again (Replace syllabus PDF) re-parses and replaces the existing "
        "breakdown.\n\n"
        "Returns 422 if the PDF has no readable text layer (a scan) or no "
        "recognisable syllabus structure — the existing syllabus is left "
        "untouched rather than being replaced with generic content."
    ),
)
async def upload_syllabus_pdf(
    subject_id: int, user: CurrentUser, db: DbSession, file: UploadFile = File(...)
) -> SubjectDetail:
    subject = _get_subject(db, user, subject_id)

    content_type = (file.content_type or "").lower()
    if content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a PDF file.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")
    if len(contents) > app_settings.MAX_SYLLABUS_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That PDF is larger than 15 MB. Please choose a smaller file.",
        )

    directory = Path(app_settings.UPLOAD_DIR) / "syllabi"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"subject{subject.id}-{secrets.token_hex(8)}.pdf"
    (directory / filename).write_bytes(contents)

    subject.syllabus_pdf_path = f"syllabi/{filename}"
    subject.syllabus_pdf_name = file.filename or "syllabus.pdf"
    subject.syllabus_status = "pdf_uploaded"
    db.add(subject)
    db.commit()

    try:
        units, detected_board = syllabus_parser.parse_pdf(contents)
    except Exception:  # noqa: BLE001 — a malformed PDF should degrade, not 500
        units, detected_board = [], None

    if not units:
        # Better to say so than to fill the syllabus with content that isn't
        # in the student's specification. Keep whatever they already had.
        subject.syllabus_status = "ready" if subject.units else "pdf_uploaded"
        db.add(subject)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "That PDF was saved, but no syllabus structure could be read from "
                "it. Scanned specifications have no text layer — try the "
                "original download from your exam board's website, or add the "
                "units and topics by hand."
            ),
        )

    subject_service.apply_parsed_units(db, subject, units)
    if detected_board and not subject.exam_board:
        subject.exam_board = detected_board

    topic_count = sum(len(topics) for _, topics in units)
    subject.syllabus_status = "ready"
    db.add(subject)
    log_activity(
        db,
        user,
        f"Generated the syllabus for {subject.name} — "
        f"{len(units)} units, {topic_count} topics",
        kind="subject",
        icon="file-check",
    )
    db.commit()
    db.refresh(subject)
    return subject_detail(subject)


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
@router.post(
    "/{subject_id}/units",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a unit",
)
def create_unit(
    subject_id: int, payload: UnitCreate, user: CurrentUser, db: DbSession
) -> UnitOut:
    subject = _get_subject(db, user, subject_id)
    unit = Unit(
        subject_id=subject.id,
        name=payload.name,
        description=payload.description,
        order_index=payload.order_index or len(subject.units),
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit_out(unit)


@router.patch("/units/{unit_id}", response_model=UnitOut, summary="Edit a unit")
def update_unit(
    unit_id: int, payload: UnitUpdate, user: CurrentUser, db: DbSession
) -> UnitOut:
    unit = _get_unit(db, user, unit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(unit, field, value)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit_out(unit)


@router.delete("/units/{unit_id}", response_model=Message, summary="Delete a unit")
def delete_unit(unit_id: int, user: CurrentUser, db: DbSession) -> Message:
    unit = _get_unit(db, user, unit_id)
    name = unit.name
    db.delete(unit)
    db.commit()
    return Message(message=f"Unit “{name}” deleted.")


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
@router.post(
    "/topics",
    response_model=TopicOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a topic to a unit",
)
def create_topic(payload: TopicCreate, user: CurrentUser, db: DbSession) -> TopicOut:
    unit = _get_unit(db, user, payload.unit_id)
    topic = Topic(
        unit_id=unit.id,
        name=payload.name,
        estimated_hours=payload.estimated_hours,
        difficulty=payload.difficulty,
        notes=payload.notes,
        order_index=len(unit.topics),
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic_out(topic)


@router.patch("/topics/{topic_id}", response_model=TopicOut, summary="Edit a topic")
def update_topic(
    topic_id: int, payload: TopicUpdate, user: CurrentUser, db: DbSession
) -> TopicOut:
    topic = _get_topic(db, user, topic_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("status") == "completed" and topic.status != "completed":
        # Route status changes through the richer completion endpoint logic.
        return _complete_topic(db, user, topic, TopicComplete())

    for field, value in data.items():
        if value is not None:
            setattr(topic, field, value)
    if data.get("status") in {"not_started", "in_progress"}:
        topic.completed_at = None

    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic_out(topic)


@router.post(
    "/topics/{topic_id}/complete",
    response_model=TopicOut,
    summary="Mark a topic complete",
    description=(
        "Records the completion, awards XP, extends the study streak and — unless "
        "you opt out — schedules the spaced-repetition ladder (2, 7 and 14 days, "
        "plus a final pass three days before the exam)."
    ),
)
def complete_topic(
    topic_id: int, payload: TopicComplete, user: CurrentUser, db: DbSession
) -> TopicOut:
    topic = _get_topic(db, user, topic_id)
    return _complete_topic(db, user, topic, payload)


def _complete_topic(db, user, topic: Topic, payload: TopicComplete) -> TopicOut:
    already_done = topic.status == "completed"
    subject = topic.unit.subject

    topic.status = "completed"
    topic.confidence = payload.confidence
    topic.completed_at = utcnow()
    db.add(topic)

    if not already_done:
        db.add(
            CompletedTopic(
                user_id=user.id,
                topic_id=topic.id,
                subject_id=subject.id,
                completed_on=date.today(),
                minutes_spent=payload.minutes_spent,
                confidence=payload.confidence,
            )
        )
        award_xp(db, user, 20)
        touch_streak(db, user)
        log_activity(
            db,
            user,
            f"Completed “{topic.name}” in {subject.name}",
            kind="topic",
            icon="check-circle",
        )

    if payload.schedule_revision:
        revision_service.schedule_for_topic(db, user, topic, subject)

    subject_service.recalculate_weak_subjects(db, user)
    db.commit()
    evaluate(db, user)
    db.commit()
    db.refresh(topic)
    return topic_out(topic)


@router.post(
    "/topics/{topic_id}/reopen",
    response_model=TopicOut,
    summary="Reopen a completed topic",
)
def reopen_topic(topic_id: int, user: CurrentUser, db: DbSession) -> TopicOut:
    topic = _get_topic(db, user, topic_id)
    topic.status = "in_progress"
    topic.completed_at = None
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic_out(topic)


@router.delete("/topics/{topic_id}", response_model=Message, summary="Delete a topic")
def delete_topic(topic_id: int, user: CurrentUser, db: DbSession) -> Message:
    topic = _get_topic(db, user, topic_id)
    name = topic.name
    db.delete(topic)
    db.commit()
    return Message(message=f"Topic “{name}” deleted.")


@router.get(
    "/{subject_id}/topics",
    response_model=List[TopicOut],
    summary="Flat topic list for a subject",
)
def list_topics(subject_id: int, user: CurrentUser, db: DbSession) -> List[TopicOut]:
    subject = _get_subject(db, user, subject_id)
    topics = db.scalars(
        select(Topic)
        .join(Unit)
        .where(Unit.subject_id == subject.id)
        .order_by(Unit.order_index, Topic.order_index)
    ).all()
    return [topic_out(t) for t in topics]
