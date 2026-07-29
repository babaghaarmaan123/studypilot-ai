"""Spaced-repetition revision schedule."""

from datetime import date
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.models import RevisionPlan
from app.schemas.common import Message
from app.schemas.planning import RevisionComplete, RevisionOut
from app.services import revision as revision_service
from app.services.achievements import evaluate
from app.services.activity import award_xp, log_activity, touch_streak
from app.services.serializers import revision_out

router = APIRouter(prefix="/revision", tags=["Revision"])


def _get_revision(db, user, revision_id: int) -> RevisionPlan:
    entry = db.get(RevisionPlan, revision_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Revision entry not found."
        )
    return entry


@router.get(
    "",
    response_model=List[RevisionOut],
    summary="Upcoming revision schedule",
    description=(
        "Every revision checkpoint within the requested window. Entries are "
        "created automatically at 2, 7 and 14 days after a topic is completed, "
        "plus a final pass three days before that subject's exam."
    ),
)
def list_revisions(
    user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=1, le=365),
) -> List[RevisionOut]:
    entries = revision_service.upcoming_revisions(db, user, days)
    return [revision_out(e) for e in entries]


@router.get("/due", response_model=List[RevisionOut], summary="Revisions due today")
def due(user: CurrentUser, db: DbSession) -> List[RevisionOut]:
    return [revision_out(e) for e in revision_service.due_revisions(db, user)]


@router.get("/stats", summary="Revision completion statistics")
def stats(user: CurrentUser, db: DbSession) -> dict:
    return revision_service.revision_stats(db, user)


@router.post(
    "/{revision_id}/complete",
    response_model=List[RevisionOut],
    summary="Complete a revision",
    description=(
        "Records how well you recalled the topic. A rating of 1 or 2 books an "
        "extra checkpoint in two days and reopens the topic, because a topic you "
        "cannot recall is not really finished."
    ),
)
def complete(
    revision_id: int,
    payload: RevisionComplete,
    user: CurrentUser,
    db: DbSession,
) -> List[RevisionOut]:
    entry = _get_revision(db, user, revision_id)
    if entry.status == "completed":
        return [revision_out(entry)]

    follow_up = revision_service.complete_revision(
        db, user, entry, payload.recall_rating
    )
    award_xp(db, user, 15)
    touch_streak(db, user)
    log_activity(
        db,
        user,
        f"Revised “{entry.topic.name}” (recall {payload.recall_rating}/5)",
        kind="revision",
        icon="repeat",
    )
    db.commit()
    evaluate(db, user)
    db.commit()

    result = [revision_out(entry)]
    if follow_up is not None:
        result.append(revision_out(follow_up))
    return result


@router.post(
    "/{revision_id}/snooze",
    response_model=RevisionOut,
    summary="Push a revision back by a day",
)
def snooze(
    revision_id: int,
    user: CurrentUser,
    db: DbSession,
    days: int = Query(1, ge=1, le=14),
) -> RevisionOut:
    from datetime import timedelta

    entry = _get_revision(db, user, revision_id)
    entry.scheduled_date = max(date.today(), entry.scheduled_date) + timedelta(days=days)
    entry.status = "pending"
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return revision_out(entry)


@router.delete("/{revision_id}", response_model=Message, summary="Delete a revision")
def delete(revision_id: int, user: CurrentUser, db: DbSession) -> Message:
    entry = _get_revision(db, user, revision_id)
    db.delete(entry)
    db.commit()
    return Message(message="Revision removed.")
