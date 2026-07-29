"""Past paper tracking and the improvement graph."""

import secrets
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.core.config import settings as app_settings
from app.core.deps import CurrentUser, DbSession
from app.models import PastPaper, Subject
from app.schemas.common import Message
from app.schemas.progress import (
    PastPaperCreate,
    PastPaperOut,
    PastPaperScore,
    PastPaperStats,
    PastPaperUpdate,
)
from app.services import past_paper_pdf
from app.services import subjects as subject_service
from app.services.achievements import evaluate
from app.services.activity import award_xp, log_activity
from app.services.serializers import past_paper_out

router = APIRouter(prefix="/past-papers", tags=["Past papers"])


def _get_paper(db, user, paper_id: int) -> PastPaper:
    paper = db.get(PastPaper, paper_id)
    if paper is None or paper.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Past paper not found."
        )
    return paper


def _grade_for(percentage: float) -> str:
    """Rough UK boundary mapping used when the student doesn't enter a grade."""
    if percentage >= 90:
        return "A*"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    if percentage >= 40:
        return "E"
    return "U"


@router.get("", response_model=List[PastPaperOut], summary="List logged past papers")
def list_papers(
    user: CurrentUser,
    db: DbSession,
    subject_id: Optional[int] = Query(None),
) -> List[PastPaperOut]:
    query = select(PastPaper).where(PastPaper.user_id == user.id)
    if subject_id is not None:
        query = query.where(PastPaper.subject_id == subject_id)
    papers = db.scalars(query.order_by(PastPaper.date_taken.desc())).all()
    return [past_paper_out(p) for p in papers]


@router.post(
    "",
    response_model=PastPaperOut,
    status_code=status.HTTP_201_CREATED,
    summary="Log a past paper",
    description=(
        "Records the score, works out the percentage and an indicative grade, "
        "then re-evaluates whether the subject counts as a weak area."
    ),
)
def create_paper(
    payload: PastPaperCreate, user: CurrentUser, db: DbSession
) -> PastPaperOut:
    subject = db.get(Subject, payload.subject_id)
    if subject is None or subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That subject does not belong to you.",
        )
    if payload.marks_scored > payload.marks_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marks scored cannot exceed the total available.",
        )

    percentage = round(payload.marks_scored / payload.marks_total * 100, 1)
    paper = PastPaper(
        user_id=user.id,
        **payload.model_dump(exclude={"grade"}),
        percentage=percentage,
        grade=payload.grade or _grade_for(percentage),
    )
    db.add(paper)
    award_xp(db, user, 25)
    log_activity(
        db,
        user,
        f"Logged {paper.title} — {percentage}%",
        kind="past_paper",
        icon="file-text",
    )
    db.commit()

    subject_service.recalculate_weak_subjects(db, user)
    db.commit()
    evaluate(db, user)
    db.commit()
    db.refresh(paper)
    return past_paper_out(paper)


@router.post(
    "/upload",
    response_model=PastPaperOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a past paper PDF",
    description=(
        "Uploads the paper itself. StudyPilot reads the cover page for the "
        "subject, exam board, year, session, paper number, total marks and "
        "time allowed, so nothing has to be typed in up front.\n\n"
        "The paper is created **unscored** — send the marks to "
        "`POST /past-papers/{id}/score` once it has been marked. Unscored "
        "papers are excluded from the averages and the improvement trend.\n\n"
        "Anything passed as a form field overrides what was read from the PDF."
    ),
)
async def upload_paper(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="The past paper PDF"),
    subject_id: Optional[int] = Form(
        None, description="Overrides the subject detected from the paper"
    ),
    title: Optional[str] = Form(None),
    date_taken: Optional[date] = Form(None),
    marks_total: Optional[float] = Form(None),
) -> PastPaperOut:
    content_type = (file.content_type or "").lower()
    filename = file.filename or "past-paper.pdf"
    if content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload the paper as a PDF.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty."
        )
    if len(contents) > app_settings.MAX_PAST_PAPER_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That PDF is larger than 25 MB. Please choose a smaller file.",
        )

    active_subjects = [s for s in user.subjects if not s.is_archived]
    if not active_subjects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a subject before uploading past papers.",
        )

    meta = past_paper_pdf.read_metadata(contents, filename, active_subjects)

    resolved_subject_id = subject_id or meta.subject_id
    if resolved_subject_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not tell which subject this paper belongs to. Choose the "
                "subject and upload it again."
            ),
        )
    subject = db.get(Subject, resolved_subject_id)
    if subject is None or subject.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That subject does not belong to you.",
        )

    directory = Path(app_settings.UPLOAD_DIR) / "past-papers"
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"paper{user.id}-{secrets.token_hex(8)}.pdf"
    (directory / stored_name).write_bytes(contents)

    paper = PastPaper(
        user_id=user.id,
        subject_id=subject.id,
        title=(title or meta.title)[:200],
        exam_board=meta.exam_board or subject.exam_board,
        year=meta.year,
        paper=meta.paper,
        session_label=meta.session_label,
        date_taken=date_taken or date.today(),
        marks_scored=0.0,
        marks_total=marks_total or meta.marks_total or 100.0,
        percentage=0.0,
        grade=None,
        time_taken_minutes=meta.time_taken_minutes,
        under_timed_conditions=True,
        scored=False,
        file_path=f"past-papers/{stored_name}",
        file_name=filename[:255],
    )
    db.add(paper)
    log_activity(
        db,
        user,
        f"Uploaded {paper.title} for {subject.name}",
        kind="past_paper",
        icon="file-up",
    )
    db.commit()
    db.refresh(paper)
    return past_paper_out(paper)


@router.post(
    "/{paper_id}/score",
    response_model=PastPaperOut,
    summary="Record the marks for an uploaded paper",
    description=(
        "Adds the score to a paper that was uploaded without one, works out the "
        "percentage and indicative grade, awards XP and re-evaluates whether the "
        "subject counts as a weak area."
    ),
)
def score_paper(
    paper_id: int, payload: PastPaperScore, user: CurrentUser, db: DbSession
) -> PastPaperOut:
    paper = _get_paper(db, user, paper_id)
    if payload.marks_scored > payload.marks_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marks scored cannot exceed the total available.",
        )

    first_score = not paper.scored
    paper.marks_scored = payload.marks_scored
    paper.marks_total = payload.marks_total
    paper.percentage = round(payload.marks_scored / payload.marks_total * 100, 1)
    paper.grade = _grade_for(paper.percentage)
    if payload.time_taken_minutes is not None:
        paper.time_taken_minutes = payload.time_taken_minutes
    if payload.under_timed_conditions is not None:
        paper.under_timed_conditions = payload.under_timed_conditions
    paper.scored = True
    db.add(paper)

    if first_score:
        award_xp(db, user, 25)
        log_activity(
            db,
            user,
            f"Scored {paper.title} — {paper.percentage}%",
            kind="past_paper",
            icon="file-text",
        )
    db.commit()

    subject_service.recalculate_weak_subjects(db, user)
    db.commit()
    evaluate(db, user)
    db.commit()
    db.refresh(paper)
    return past_paper_out(paper)


@router.patch("/{paper_id}", response_model=PastPaperOut, summary="Edit a past paper")
def update_paper(
    paper_id: int, payload: PastPaperUpdate, user: CurrentUser, db: DbSession
) -> PastPaperOut:
    paper = _get_paper(db, user, paper_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(paper, field, value)

    if paper.marks_total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total marks must be greater than zero.",
        )
    if data.get("marks_scored") is not None:
        # Editing in a score counts as scoring the paper.
        paper.scored = True
    paper.percentage = round(paper.marks_scored / paper.marks_total * 100, 1)
    if not payload.grade:
        paper.grade = _grade_for(paper.percentage) if paper.scored else None

    db.add(paper)
    db.commit()
    subject_service.recalculate_weak_subjects(db, user)
    db.commit()
    db.refresh(paper)
    return past_paper_out(paper)


@router.delete("/{paper_id}", response_model=Message, summary="Delete a past paper")
def delete_paper(paper_id: int, user: CurrentUser, db: DbSession) -> Message:
    paper = _get_paper(db, user, paper_id)
    title = paper.title
    stored = paper.file_path
    db.delete(paper)
    db.commit()

    if stored:
        # Best effort — a missing file must not fail the delete.
        try:
            (Path(app_settings.UPLOAD_DIR) / stored).unlink(missing_ok=True)
        except OSError:
            pass
    return Message(message=f"{title} deleted.")


@router.get(
    "/stats",
    response_model=PastPaperStats,
    summary="Averages, best score and improvement trend",
)
def stats(user: CurrentUser, db: DbSession) -> PastPaperStats:
    all_papers = db.scalars(
        select(PastPaper)
        .where(PastPaper.user_id == user.id)
        .order_by(PastPaper.date_taken)
    ).all()

    # A paper uploaded but not yet marked has no score to average.
    papers = [p for p in all_papers if p.scored]
    awaiting = len(all_papers) - len(papers)

    if not papers:
        return PastPaperStats(
            total_papers=0,
            awaiting_score=awaiting,
            average_percentage=0.0,
            best_percentage=0.0,
            latest_percentage=0.0,
            improvement=0.0,
            by_subject=[],
            trend=[],
        )

    scores = [p.percentage for p in papers]
    if len(scores) < 2:
        improvement = 0.0
    elif len(scores) < 6:
        # Too few papers for rolling averages — compare latest to first.
        improvement = round(scores[-1] - scores[0], 1)
    else:
        # Rolling: the last three papers versus the first three.
        head, tail = scores[:3], scores[-3:]
        improvement = round(sum(tail) / 3 - sum(head) / 3, 1)

    grouped = defaultdict(list)
    for paper in papers:
        grouped[paper.subject_id].append(paper)

    by_subject = []
    for subject_id, rows in grouped.items():
        subject = rows[0].subject
        subject_scores = [r.percentage for r in rows]
        by_subject.append(
            {
                "subject_id": subject_id,
                "name": subject.name if subject else "Unknown",
                "colour": subject.colour if subject else "#6366f1",
                "count": len(rows),
                "average": round(sum(subject_scores) / len(subject_scores), 1),
                "best": max(subject_scores),
                "latest": subject_scores[-1],
            }
        )
    by_subject.sort(key=lambda r: r["average"], reverse=True)

    return PastPaperStats(
        total_papers=len(papers),
        awaiting_score=awaiting,
        average_percentage=round(sum(scores) / len(scores), 1),
        best_percentage=max(scores),
        latest_percentage=scores[-1],
        improvement=improvement,
        by_subject=by_subject,
        trend=[
            {
                "label": p.date_taken.strftime("%d %b"),
                "date": p.date_taken.isoformat(),
                "percentage": p.percentage,
                "subject": p.subject.name if p.subject else "",
                "colour": p.subject.colour if p.subject else "#6366f1",
                "title": p.title,
            }
            for p in papers
        ],
    )
