"""Achievements, XP and badges."""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.progress import AchievementSummary
from app.services.achievements import DEFINITIONS, evaluate
from app.services.activity import xp_progress
from app.services.serializers import achievement_out

router = APIRouter(prefix="/achievements", tags=["Achievements"])


@router.get(
    "",
    response_model=AchievementSummary,
    summary="Achievements, XP and level",
    description=(
        "Re-evaluates every achievement against your latest activity, unlocking "
        "any you have just earned, and returns the full badge list with progress."
    ),
)
def list_achievements(user: CurrentUser, db: DbSession) -> AchievementSummary:
    evaluate(db, user)
    db.commit()
    db.refresh(user)

    level, into, needed = xp_progress(user.xp)
    achievements = sorted(
        user.achievements,
        key=lambda a: (a.unlocked_at is None, -a.progress, a.name),
    )
    return AchievementSummary(
        xp=user.xp,
        level=level,
        xp_into_level=into,
        xp_for_next_level=needed,
        unlocked_count=sum(1 for a in achievements if a.unlocked),
        total_count=len(DEFINITIONS),
        streak_current=user.streak_current,
        streak_longest=user.streak_longest,
        achievements=[achievement_out(a) for a in achievements],
    )
