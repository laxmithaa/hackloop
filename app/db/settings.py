"""Database settings, read from environment variables or a local .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in the repo root and in backend/, whichever folder you run from.
_BACKEND = Path(__file__).resolve().parents[2]
_ENV_FILES = (_BACKEND / ".env",)


class DbSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        extra="ignore",
        case_sensitive=False,
    )

    #: Connection string for PostgreSQL. Read from the unprefixed
    #: ``DATABASE_URL`` environment variable (or the local .env file), which
    #: is what psql, docker-compose and the docs all use.
    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # Access-code rules from the requirements: 3 attempts, 5-minute window.
    access_max_attempts: int = 3
    access_entry_window_minutes: int = 5
    # How long a verified session stays open after the code is accepted.
    # ASSUMPTION: the requirements do not say. Confirm with the team.
    verified_session_minutes: int = 30
    # Cap on free-text follow-up questions per verified session.
    max_questions_per_session: int = 10


def get_db_settings() -> DbSettings:
    return DbSettings()
