"""Bring a database up to date and prove the app can serve from it.

    python -m scripts.bootstrap                # migrate, then verify
    python -m scripts.bootstrap --check-only   # verify without migrating
    python -m scripts.bootstrap --demo-user    # also create a demo account

StudyPilot needs no seed rows: every piece of reference data - the subject
catalogue, admission exams, syllabus templates and achievement definitions -
lives in `app/data` and `app/services`, so it ships with the code and cannot
drift from it. What this script checks is that the schema is at the migration
head and that the reference data actually loads, which is the useful half of
"seeding" for this application.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from sqlalchemy import inspect

from app.core.config import settings
from app.data.catalog import ADMISSION_EXAMS, subjects_for
from app.data.syllabus import template_for
from app.db.base import Base
from app.db.session import SessionLocal, engine

# Importing the models package registers every table on Base.metadata.
from app import models  # noqa: F401  (side-effect import)

DEMO_EMAIL = "demo@studypilot.app"
DEMO_PASSWORD = "StudyPilotDemo!2026"


def _redacted_url() -> str:
    """The database URL with any password removed, safe for logs."""
    url = engine.url
    return str(url.set(password="***")) if url.password else str(url)


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    print(f"-> migrating {_redacted_url()}")
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def _schema_report() -> Tuple[bool, List[str]]:
    inspector = inspect(engine)
    present = set(inspector.get_table_names())
    expected = set(Base.metadata.tables)
    missing = sorted(expected - present)

    notes = [f"tables: {len(expected & present)}/{len(expected)} present"]
    if "alembic_version" in present:
        with engine.connect() as connection:
            from sqlalchemy import text

            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        notes.append(f"migration revision: {revision}")
    else:
        notes.append("migration revision: none (alembic_version table absent)")

    if missing:
        notes.append(f"MISSING TABLES: {', '.join(missing)}")
    return not missing, notes


def _reference_data_report() -> Tuple[bool, List[str]]:
    notes: List[str] = []
    ok = True

    for curriculum in ("gcse", "a_level", "international_a_level"):
        count = len(subjects_for(curriculum))
        notes.append(f"{curriculum}: {count} subjects")
        ok = ok and count > 0

    notes.append(f"admission exams: {len(ADMISSION_EXAMS)}")
    ok = ok and bool(ADMISSION_EXAMS)

    # A template lookup is the path onboarding takes for every new subject.
    sample = template_for("Mathematics", "a_level")
    topics = sum(len(v) for v in sample.values())
    notes.append(f"syllabus template probe (A level Mathematics): "
                 f"{len(sample)} units / {topics} topics")
    ok = ok and topics > 0
    return ok, notes


def _row_counts() -> List[str]:
    from sqlalchemy import func, select

    notes = []
    with SessionLocal() as session:
        for name in ("users", "subjects", "topics", "study_sessions", "past_papers"):
            table = Base.metadata.tables.get(name)
            if table is None:
                continue
            count = session.scalar(select(func.count()).select_from(table))
            notes.append(f"{name}: {count}")
    return notes


def create_demo_user() -> None:
    """An account to smoke-test a fresh deployment with. Idempotent."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.models import User, UserSettings

    with SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing is not None:
            print(f"-> demo user already present: {DEMO_EMAIL}")
            return
        user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            name="Demo Student",
        )
        user.settings = UserSettings()
        session.add(user)
        session.commit()
        print(f"-> created demo user {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("  (onboarding not completed - sign in and it will prompt)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only", action="store_true", help="verify without migrating"
    )
    parser.add_argument(
        "--demo-user", action="store_true", help="create a demo account to test with"
    )
    args = parser.parse_args()

    print(f"StudyPilot bootstrap | env={settings.ENVIRONMENT} | "
          f"engine={'sqlite' if settings.is_sqlite else 'postgresql'}")
    print(f"database: {_redacted_url()}\n")

    if not args.check_only:
        migrate()
        print()

    schema_ok, schema_notes = _schema_report()
    reference_ok, reference_notes = _reference_data_report()

    print("schema")
    for note in schema_notes:
        print(f"  {note}")
    print("\nreference data (ships with the code - nothing to seed)")
    for note in reference_notes:
        print(f"  {note}")

    if schema_ok:
        print("\nrow counts")
        for note in _row_counts():
            print(f"  {note}")

    if args.demo_user and schema_ok:
        print()
        create_demo_user()

    ok = schema_ok and reference_ok
    print(f"\n{'OK - ready to serve' if ok else 'FAILED - see above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
