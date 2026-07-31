"""ORM models.

Imported for its side effects: every model must be registered on
``Base.metadata`` before ``create_all`` / Alembic autogenerate runs.
"""

from app.models.academic import (  # noqa: F401
    CompletedTopic,
    Exam,
    Subject,
    Topic,
    Unit,
)
from app.models.planning import RevisionPlan, StudyPlan, StudySession  # noqa: F401
from app.models.progress import (  # noqa: F401
    Achievement,
    ActivityLog,
    Notification,
    PastPaper,
)
from app.models.user import (  # noqa: F401
    AdmissionExam,
    PasswordResetCode,
    TargetUniversity,
    User,
    UserSettings,
)

__all__ = [
    "User",
    "UserSettings",
    "TargetUniversity",
    "AdmissionExam",
    "PasswordResetCode",
    "Subject",
    "Unit",
    "Topic",
    "CompletedTopic",
    "Exam",
    "StudyPlan",
    "StudySession",
    "RevisionPlan",
    "PastPaper",
    "Achievement",
    "Notification",
    "ActivityLog",
]
