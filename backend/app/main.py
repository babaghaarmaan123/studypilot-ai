"""StudyPilot AI — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db.init_db import init_db

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger("studypilot")


@asynccontextmanager
async def lifespan(_: FastAPI):
    for folder in ("avatars", "syllabi", "past-papers"):
        Path(settings.UPLOAD_DIR, folder).mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(
        "StudyPilot AI %s ready · env=%s · db=%s · uploads=%s",
        __version__,
        settings.ENVIRONMENT,
        "sqlite" if settings.is_sqlite else "postgresql",
        settings.UPLOAD_DIR,
    )
    yield
    logger.info("StudyPilot AI shutting down")


DESCRIPTION = """
The StudyPilot AI backend — an AI-powered study planner for students on the UK
education system.

**Supported curricula:** GCSE, A Levels and International A Levels.
StudyPilot does not support undergraduate, postgraduate, Foundation Programme
or IB Diploma study.

### How the pieces fit together

1. **Register** → the account starts with `onboarding_completed = false`.
2. **Onboarding** (`/onboarding/complete`) captures the 10 answers, creates the
   student's subjects with a seeded syllabus, records their exam timetable and
   generates the first 28-day plan.
3. **The AI study engine** (`/plans/generate`) scores every subject on exam
   proximity, difficulty, priority, weak-subject status and remaining syllabus,
   then fills each day block by block.
4. **Completing a topic** books spaced-repetition revisions at 2, 7 and 14 days
   plus a final pass three days before the exam.
5. **Missing sessions** feeds `/plans/regenerate`, which redistributes the
   outstanding work.

### Authentication

Every endpoint outside `/catalog` and `/auth` expects
`Authorization: Bearer <access_token>`.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "StudyPilot AI"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Covers Vercel preview deployments, whose hostname changes per commit.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

register_exception_handlers(app)

# Mounted at import time as well as in the lifespan, because StaticFiles
# checks the directory exists the moment it is constructed.
for _folder in ("avatars", "syllabi", "past-papers"):
    Path(settings.UPLOAD_DIR, _folder).mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads"
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"], summary="Service metadata")
def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "version": __version__,
        "status": "ok",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
        "supported_curricula": ["GCSE", "A Levels", "International A Levels"],
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description=(
        "Liveness plus a one-round-trip database check. Always answers 200 so a "
        "platform health check does not restart the service over a transient "
        "database blip — read `database` to see whether queries are working."
    ),
)
def health() -> dict:
    from sqlalchemy import text

    from app.db.session import engine

    database = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:  # noqa: BLE001 — reported, not raised
        logger.error("Health check database probe failed: %s", error)
        database = "error"

    return {
        "status": "healthy",
        "database": database,
        "engine": "sqlite" if settings.is_sqlite else "postgresql",
        "environment": settings.ENVIRONMENT,
        "version": __version__,
    }
