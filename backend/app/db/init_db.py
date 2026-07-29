"""Schema creation.

For SQLite in development `create_all` is enough, plus the additive column
sync below so an existing dev database picks up newly added model columns
without being deleted. On PostgreSQL you would put Alembic in front of this —
the models are already written so that `alembic revision --autogenerate`
produces a usable first migration.
"""

import logging

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Importing the models package registers every table on Base.metadata.
from app import models  # noqa: F401  (side-effect import)

logger = logging.getLogger(__name__)


def _sync_sqlite_columns() -> None:
    """`ALTER TABLE ... ADD COLUMN` for model columns the database lacks.

    Deliberately additive only: SQLite cannot drop or retype a column without
    rebuilding the table, and silently rebuilding a student's data is not
    something a dev convenience should do. Anything that needs more than a new
    nullable/defaulted column is a real migration.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue

            default = column.default.arg if column.default is not None else None
            if column.nullable:
                clause = f"{column.name} {column.type.compile(engine.dialect)}"
            elif default is not None and not callable(default):
                literal = (
                    ("1" if default else "0")
                    if isinstance(default, bool)
                    else (f"'{default}'" if isinstance(default, str) else str(default))
                )
                clause = (
                    f"{column.name} {column.type.compile(engine.dialect)} "
                    f"NOT NULL DEFAULT {literal}"
                )
            else:
                logger.warning(
                    "Cannot add %s.%s automatically — needs a real migration",
                    table.name,
                    column.name,
                )
                continue

            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {clause}"))
            logger.info("Added missing column %s.%s", table.name, column.name)


def init_db() -> None:
    """Prepare the schema for the database we are pointed at.

    On SQLite (local development) the schema is created straight from the
    models, which keeps `git clone && run` working with no extra step.

    On PostgreSQL the schema belongs to Alembic: the deploy runs
    `alembic upgrade head` before the server starts (see `render.yaml`), so
    creating tables here as well would race the migration and leave the
    `alembic_version` table out of step with reality.
    """
    if settings.is_sqlite:
        Base.metadata.create_all(bind=engine)
        _sync_sqlite_columns()
        logger.info("SQLite schema ready (%d tables)", len(Base.metadata.tables))
        return

    logger.info(
        "PostgreSQL detected — schema is managed by Alembic "
        "(`alembic upgrade head` runs at deploy time)"
    )
