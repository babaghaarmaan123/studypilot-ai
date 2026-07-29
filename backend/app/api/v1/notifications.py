"""In-app notifications and the activity feed."""

from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, update

from app.core.deps import CurrentUser, DbSession
from app.models import ActivityLog, Notification
from app.schemas.common import Message
from app.schemas.progress import ActivityOut, NotificationOut
from app.services.serializers import activity_out

router = APIRouter(tags=["Notifications"])


@router.get(
    "/notifications", response_model=List[NotificationOut], summary="List notifications"
)
def list_notifications(
    user: CurrentUser,
    db: DbSession,
    unread_only: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
) -> List[NotificationOut]:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    rows = db.scalars(
        query.order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    return [NotificationOut.model_validate(n) for n in rows]


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark one notification read",
)
def mark_read(
    notification_id: int, user: CurrentUser, db: DbSession
) -> NotificationOut:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    note.is_read = True
    db.add(note)
    db.commit()
    db.refresh(note)
    return NotificationOut.model_validate(note)


@router.post(
    "/notifications/read-all", response_model=Message, summary="Mark all read"
)
def mark_all_read(user: CurrentUser, db: DbSession) -> Message:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return Message(message="All notifications marked as read.")


@router.delete(
    "/notifications/{notification_id}", response_model=Message, summary="Delete one"
)
def delete_notification(
    notification_id: int, user: CurrentUser, db: DbSession
) -> Message:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    db.delete(note)
    db.commit()
    return Message(message="Notification deleted.")


@router.get("/activity", response_model=List[ActivityOut], summary="Recent activity")
def activity(
    user: CurrentUser, db: DbSession, limit: int = Query(20, ge=1, le=100)
) -> List[ActivityOut]:
    rows = db.scalars(
        select(ActivityLog)
        .where(ActivityLog.user_id == user.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    ).all()
    return [activity_out(a) for a in rows]
