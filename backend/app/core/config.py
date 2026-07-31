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

    # --- Password reset codes ---------------------------------------------
    #: Short expiry and a hard attempt cap are what make a six digit code safe:
    #: there are only a million of them, so it must not stay guessable for long.
    RESET_CODE_EXPIRE_MINUTES: int = 15
    RESET_CODE_MAX_ATTEMPTS: int = 5
    #: Minimum gap between codes for one account, so the endpoint cannot be used
    #: to bombard somebody's inbox.
    RESET_CODE_RESEND_SECONDS: int = 60

    # --- Outbound email ----------------------------------------------------
    # Two ways to send, because one of them does not work everywhere:
    #
    #   `smtp`   classic SMTP. Works locally and on any normal host, but Render
    #            blocks outbound ports 25, 465 and 587 on free web services
    #            (since 26 September 2025), so on a free instance every send
    #            times out. Fine on a paid instance.
    #   `brevo`  Brevo's HTTPS API. Port 443, so it is unaffected by that block,
    #            and a single sender address can be verified without owning a
    #            domain. The right choice on Render's free tier.
    #   `resend` Resend's HTTPS API. Also unaffected, but needs a verified
    #            domain to send to arbitrary recipients.
    #
    # Unset means nothing is sent and the code is written to the log instead,
    # which is what you want locally and must never be what happens in
    # production. See `_guard_production` below.
    #: Shared secret for the scheduled-task endpoints, which no logged-in user
    #: owns and so cannot be protected by a normal JWT. Unset means those
    #: endpoints refuse every request, which is the right default: an open
    #: trigger is a way to make the app email everybody on demand.
    TASK_SECRET: Optional[str] = None

    EMAIL_PROVIDER: str = "smtp"
    #: API key for `brevo` or `resend`. Ignored by the `smtp` provider.
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_API_TIMEOUT_SECONDS: int = 20

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    #: STARTTLS on 587 (the usual choice). Set SMTP_USE_SSL for implicit TLS on 465.
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 20
    #: Envelope sender. Many providers require this to match an address or
    #: domain you have verified with them, so it falls back to the username.
    EMAIL_FROM: Optional[str] = None
    EMAIL_FROM_NAME: str = "StudyPilot AI"

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

    @field_validator(
        "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", mode="before"
    )
    @classmethod
    def _trim_smtp(cls, value):
        """Trim stray whitespace around SMTP settings.

        Google displays an app password as four groups of four, so it is very
        easy to paste `SMTP_PASSWORD= abcd efgh ...` with a leading space. The
        surrounding whitespace survives .env parsing and the login then fails
        with an authentication error that says nothing about the real cause.
        Only the outside is trimmed: a password may legitimately contain a
        space, and Google accepts an app password with or without its own.
        """
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
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
        if not self.email_enabled:
            # Not fatal: everything except password reset works without mail.
            # Loud, because a student who forgets their password has no way back
            # into their account until this is set.
            logger.error(
                "Email is not configured in production: password reset codes "
                "cannot be delivered. Either set EMAIL_PROVIDER=brevo with "
                "EMAIL_API_KEY and EMAIL_FROM, or EMAIL_PROVIDER=smtp with "
                "SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and EMAIL_FROM."
            )
        elif self.email_provider == "smtp":
            # Render blocks outbound 25/465/587 on free web services, so SMTP
            # there fails with a connection timeout that looks like a wrong
            # password. Flagged at start-up rather than left to be rediscovered
            # from a silent inbox.
            logger.warning(
                "Email is set to the smtp provider. If this is running on a "
                "free Render web service, outbound SMTP ports are blocked and "
                "sends will time out; use EMAIL_PROVIDER=brevo instead, or a "
                "paid instance."
            )
        return self

    @property
    def email_from_address(self) -> Optional[str]:
        return self.EMAIL_FROM or self.SMTP_USERNAME

    @property
    def email_provider(self) -> str:
        return (self.EMAIL_PROVIDER or "smtp").strip().lower()

    @property
    def email_enabled(self) -> bool:
        """Whether there is somewhere to actually hand a message to."""
        if not self.email_from_address:
            return False
        if self.email_provider in {"brevo", "resend"}:
            return bool(self.EMAIL_API_KEY)
        return bool(self.SMTP_HOST)

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
