"""Alembic environment.

The database URL always comes from the application settings, and therefore from
`DATABASE_URL`, rather than from `alembic.ini` — that way `alembic upgrade head`
targets exactly the database the app is about to serve, on a laptop or on
Render, with no second place to keep in sync.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Importing the models package registers every table on Base.metadata.
from app import models  # noqa: F401  (side-effect import)

config = context.config

# `%` is the interpolation character in .ini files, so escape any in a password.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_object(object_, name, type_, reflected, compare_to) -> bool:
    """Keep Alembic's attention on our own tables."""
    return not (type_ == "table" and name == "alembic_version")


#: SQLite cannot ALTER most things in place; batch mode rewrites the table
#: instead, so one migration script runs on SQLite and on PostgreSQL.
_COMMON = {
    "target_metadata": target_metadata,
    "compare_type": True,
    "compare_server_default": True,
    "include_object": _include_object,
    "render_as_batch": settings.is_sqlite,
}


def run_migrations_offline() -> None:
    """Emit SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=settings.DATABASE_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_COMMON,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, **_COMMON)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
