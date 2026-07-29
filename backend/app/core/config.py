"""Application configuration.

All settings are environment driven so the exact same image can run locally on
SQLite and in production on PostgreSQL without a code change.
"""

import logging
import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

#: The shipped placeholder. Refused in production.
INSECURE_SECRET_KEY = "change-me-in-production-please-use-a-long-random-string"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---------------------------------------------------------------
    PROJECT_NAME: str = "StudyPilot AI"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- Database ----------------------------------------------------------
    # SQLite by default. Set DATABASE_URL to a PostgreSQL URL in production —
    # Render's "Internal Database URL" can be pasted in as-is, the validator
    # below rewrites the legacy `postgres://` scheme SQLAlchemy 2 rejects.
    DATABASE_URL: str = "sqlite:///./studypilot.db"

    # --- Security ----------------------------------------------------------
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24          # 1 day
    REMEMBER_ME_EXPIRE_MINUTES: int = 60 * 24 * 30      # 30 days
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # --- CORS --------------------------------------------------------------
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://localhost:3000",
    ]
    #: The deployed frontend. Set this on the host so a custom domain is
    #: allowed too — the Vercel preview regex only covers *.vercel.app.
    FRONTEND_URL: Optional[str] = None

    # --- Uploads -----------------------------------------------------------
    # Point this at a mounted disk in production; a container's own filesystem
    # is wiped on every deploy, taking uploaded syllabi and papers with it.
    UPLOAD_DIR: str = "uploads"
    MAX_AVATAR_BYTES: int = 4 * 1024 * 1024  # 4 MB
    MAX_SYLLABUS_PDF_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MAX_PAST_PAPER_BYTES: int = 25 * 1024 * 1024  # 25 MB

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalise_database_url(cls, value):
        """Accept the `postgres://` URLs hosting providers hand out."""
        if not isinstance(value, str):
            return value
        url = value.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg2://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg2://" + url[len("postgresql://") :]
        return url

    @model_validator(mode="after")
    def _guard_production(self):
        if not self.is_production:
            return self

        if self.SECRET_KEY == INSECURE_SECRET_KEY:
            # Never serve production traffic with the published signing key —
            # anyone could mint a valid token for any account.
            raise ValueError(
                "SECRET_KEY must be set to a private random value when "
                "ENVIRONMENT=production. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if self.DEBUG:
            logger.warning("DEBUG is on in production — turning it off")
            self.DEBUG = False
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def cors_origins(self) -> List[str]:
        """Configured origins plus the deployed frontend, de-duplicated."""
        origins = list(self.BACKEND_CORS_ORIGINS)
        if self.FRONTEND_URL:
            frontend = self.FRONTEND_URL.rstrip("/")
            if frontend not in origins:
                origins.append(frontend)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


def generate_secret_key() -> str:
    """Convenience for the deploy scripts and the README."""
    return secrets.token_urlsafe(64)


settings = get_settings()
