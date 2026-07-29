"""Database engine / session factory.

The engine keyword arguments are the only place that knows which backend we are
on, which is what keeps the SQLite -> PostgreSQL move a configuration change.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

if settings.is_sqlite:
    engine_kwargs = {
        # SQLite + FastAPI's threadpool need this; harmless everywhere else.
        "connect_args": {"check_same_thread": False},
    }
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }

engine = create_engine(settings.DATABASE_URL, future=True, **engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
