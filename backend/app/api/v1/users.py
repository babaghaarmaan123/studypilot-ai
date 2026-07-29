"""Profile, avatar upload, settings and account deletion."""

import secrets
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings as app_settings
from app.core.deps import CurrentUser, DbSession
from app.models import TargetUniversity, UserSettings
from app.schemas.auth import (
    ProfileUpdate,
    UserOut,
    UserSettingsOut,
    UserSettingsUpdate,
)
from app.schemas.common import Message
from app.services import mentor
from app.services import subjects as subject_service
from app.services.activity import log_activity, notify
from app.services.planner import active_plan
from app.services.serializers import load_json_list, user_out

router = APIRouter(prefix="/users", tags=["Profile & settings"])

#: Profile fields the AI Academic Mentor summary is written from. The summary is
#: a stored snapshot, so editing any of these without regenerating it leaves the
#: dashboard describing a year group or curriculum the student no longer has.
_SUMMARY_FIELDS = frozenset(
    {
        "year_group",
        "curriculum",
        "target_degree",
        "weekday_hours",
        "weekend_hours",
        "preferred_study_time",
        "study_habits",
    }
)

_ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update the student profile",
    description=(
        "Partial update — send only the fields you want to change. Setting "
        "`universities` replaces the whole list.\n\n"
        "Changing anything the mentor summary is built from also regenerates "
        "that summary, so the dashboard cannot keep describing the old profile.\n\n"
        "**Changing `curriculum` deletes the subjects belonging to the old one**, "
        "along with their syllabus, timetabled sessions, revisions and logged "
        "past papers — a GCSE student has no use for A Level modules. The exam "
        "timetable and study plan are rebuilt by re-running onboarding "
        "(`POST /onboarding/complete`)."
    ),
)
def update_profile(payload: ProfileUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    import json

    data = payload.model_dump(exclude_unset=True)
    universities = data.pop("universities", None)
    habits = data.pop("study_habits", None)
    previous_curriculum = user.curriculum

    for field, value in data.items():
        if value is not None:
            setattr(user, field, value)

    if habits is not None:
        user.study_habits = json.dumps(habits)

    if universities is not None:
        # Reassigning the collection lets the delete-orphan cascade remove the
        # old rows. Deleting them by hand would conflict with `db.add(user)`.
        user.universities = [
            TargetUniversity(name=name) for name in dict.fromkeys(universities)
        ]

    db.add(user)
    db.flush()

    # Switching course makes the old course's subjects meaningless, so they go
    # with it rather than lingering on the Subjects page under the wrong
    # curriculum. Deliberately destructive: the syllabus, sessions, revisions
    # and logged past papers for those subjects go too.
    removed: list[str] = []
    if user.curriculum and user.curriculum != previous_curriculum:
        removed = subject_service.prune_for_curriculum(db, user, user.curriculum)

    touched_summary = bool(_SUMMARY_FIELDS & set(data)) or habits is not None
    if touched_summary and user.onboarding_completed:
        db.flush()
        mentor.refresh_summary(db, user, active_plan(db, user))

    if removed:
        listed = ", ".join(removed[:6]) + ("…" if len(removed) > 6 else "")
        log_activity(
            db,
            user,
            f"Switched to {user.curriculum} and removed "
            f"{len(removed)} subject(s): {listed}",
            kind="account",
            icon="trash-2",
        )
        notify(
            db,
            user,
            title=f"{len(removed)} subject(s) removed",
            message=(
                f"They belonged to your previous curriculum: {listed}. "
                "Add the subjects you are studying now from the Subjects page."
            ),
            kind="warning",
            link="/subjects",
        )
    else:
        log_activity(db, user, "Updated your profile", kind="account", icon="user-round")

    db.commit()
    db.refresh(user)
    return user_out(user)


@router.post(
    "/me/avatar",
    response_model=UserOut,
    summary="Upload a profile picture",
    description="Accepts PNG, JPEG, WebP or GIF up to 4 MB.",
)
async def upload_avatar(
    user: CurrentUser, db: DbSession, file: UploadFile = File(...)
) -> UserOut:
    extension = _ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a PNG, JPEG, WebP or GIF image.",
        )

    contents = await file.read()
    if len(contents) > app_settings.MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="That image is larger than 4 MB. Please choose a smaller one.",
        )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty."
        )

    directory = Path(app_settings.UPLOAD_DIR) / "avatars"
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"user{user.id}-{secrets.token_hex(8)}{extension}"
    (directory / filename).write_bytes(contents)

    # Remove the previous file so uploads do not accumulate.
    if user.avatar_url:
        old = Path(app_settings.UPLOAD_DIR) / Path(user.avatar_url).name
        old_avatar = directory / Path(user.avatar_url).name
        for candidate in (old_avatar, old):
            try:
                if candidate.is_file():
                    candidate.unlink()
            except OSError:
                pass

    user.avatar_url = f"/uploads/avatars/{filename}"
    db.add(user)
    log_activity(db, user, "Updated your profile picture", kind="account", icon="image")
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.delete(
    "/me/avatar", response_model=UserOut, summary="Remove the profile picture"
)
def delete_avatar(user: CurrentUser, db: DbSession) -> UserOut:
    if user.avatar_url:
        path = Path(app_settings.UPLOAD_DIR) / "avatars" / Path(user.avatar_url).name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
    user.avatar_url = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.get("/me/settings", response_model=UserSettingsOut, summary="Read settings")
def get_settings(user: CurrentUser, db: DbSession) -> UserSettingsOut:
    if user.settings is None:
        user.settings = UserSettings()
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserSettingsOut.model_validate(user.settings)


@router.patch(
    "/me/settings", response_model=UserSettingsOut, summary="Update settings"
)
def update_settings(
    payload: UserSettingsUpdate, user: CurrentUser, db: DbSession
) -> UserSettingsOut:
    if user.settings is None:
        user.settings = UserSettings()
        db.flush()

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user.settings, field, value)

    db.add(user.settings)
    db.commit()
    db.refresh(user)
    return UserSettingsOut.model_validate(user.settings)


@router.get(
    "/me/export",
    summary="Export the timetable as structured data",
    description=(
        "Returns the student's profile, subjects, exams and upcoming sessions. "
        "The frontend renders this to PDF client-side so no server-side "
        "typesetting dependency is required."
    ),
)
def export_timetable(user: CurrentUser, db: DbSession) -> dict:
    from datetime import date, timedelta

    from app.services.planner import sessions_between
    from app.services.serializers import exam_out, session_out, subject_out

    today = date.today()
    sessions = sessions_between(db, user, today, today + timedelta(days=27))

    return {
        "generated_on": today.isoformat(),
        "student": {
            "name": user.name,
            "email": user.email,
            "year_group": user.year_group,
            "curriculum": user.curriculum,
            "target_degree": user.target_degree,
            "universities": [u.name for u in user.universities],
            "admission_exams": [e.code for e in user.admission_exams],
            "study_habits": load_json_list(user.study_habits),
            "weekday_hours": user.weekday_hours,
            "weekend_hours": user.weekend_hours,
            "preferred_study_time": user.preferred_study_time,
        },
        "subjects": [subject_out(s).model_dump(mode="json") for s in user.subjects],
        "exams": [
            exam_out(e).model_dump(mode="json")
            for e in sorted(user.exams, key=lambda e: e.exam_date)
        ],
        "sessions": [session_out(s).model_dump(mode="json") for s in sessions],
        "mentor_summary": user.mentor_summary,
    }


@router.delete(
    "/me",
    response_model=Message,
    summary="Delete the account",
    description=(
        "Permanently deletes the account and every related record "
        "(subjects, plans, sessions, papers, achievements). This cannot be undone."
    ),
)
def delete_account(user: CurrentUser, db: DbSession) -> Message:
    if user.avatar_url:
        path = Path(app_settings.UPLOAD_DIR) / "avatars" / Path(user.avatar_url).name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    db.delete(user)
    db.commit()
    return Message(message="Your account and all associated data have been deleted.")
