"""Environment-driven application configuration.

Every setting is read from the process environment (or the local ``.env`` file)
using the ``HBN_`` prefix, for example ``HBN_ENVIRONMENT``. Only non-sensitive
defaults live here; nothing reads or prints secret values.

Phase 1 has no persistence layer, so there is deliberately no database setting
yet. Later phases add their own settings under the same prefix.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Root of this backend project (the directory that contains ``app/``).
BACKEND_DIR = Path(__file__).resolve().parents[2]

Environment = Literal["local", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

#: Secret values that must never be deployed as real credentials.
_PLACEHOLDER_TOKENS = frozenset(
    {
        "changeme",
        "change-me",
        "admin",
        "password",
        "secret",
        "token",
        "dummy",
        "placeholder",
        "todo",
        "fixme",
        "not-a-secret",
    }
)

#: Development-only CORS origins. Shipping these to production signals that
#: the real deployment origins were never configured, so production mode
#: rejects them.
_DEV_DEFAULT_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5173",
)


def parse_origin_list(raw: str | list[str]) -> list[str]:
    """Parse and validate a comma-separated list or JSON array of CORS origins.

    Origins are normalised (whitespace removed, trailing slash dropped,
    duplicates collapsed) so that a malformed configuration fails at startup
    instead of at the first cross-origin request.
    """

    if isinstance(raw, list):
        values = raw
    else:
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "CORS origins must be a comma-separated list or a JSON array of strings."
                ) from exc
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise ValueError(
                    "CORS origins must be a comma-separated list or a JSON array of strings."
                )
            values = parsed
        else:
            values = text.split(",")

    origins: list[str] = []
    for value in values:
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            origins.append(origin)
            continue
        parts = urlsplit(origin)
        if parts.scheme not in {"http", "https"} or not parts.netloc or parts.path:
            raise ValueError(f"Invalid CORS origin {origin!r}. Expected 'scheme://host[:port]'.")
        if parts.query or parts.fragment:
            raise ValueError(
                f"Invalid CORS origin {origin!r}. Query strings and fragments are not allowed."
            )
        origins.append(origin)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(origins))


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_prefix="HBN_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Healthcare Bill Navigator API"
    app_version: str = "0.1.0"
    environment: Environment = "local"

    #: Optional PostgreSQL URL. Empty keeps the prototype's in-memory mode.
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    api_v1_prefix: str = "/api/v1"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = True

    log_level: LogLevel = "INFO"
    request_id_header: str = "X-Request-ID"

    # --- Phase 2: sessions, consent, uploads and OCR ---
    # Sessions remain process-local until the API workflow is migrated to DB storage.

    #: How long an in-memory patient session stays valid after creation.
    session_ttl_minutes: int = Field(default=60, ge=1, le=1440)

    #: Server-side version of the consent text patients accept.
    consent_policy_version: str = "patient-consent-2026-10-v1"

    #: Ceiling for one bill-image upload (JPEG/PNG/WebP). Nothing is stored permanently.
    bill_upload_max_size_mb: int = Field(default=5, ge=1, le=25)

    #: Largest image side (width or height) accepted after decoding.
    image_max_dimension_px: int = Field(default=5000, ge=100, le=20000)

    #: OCR text below this mean word-confidence (0-100) is treated as unreadable.
    ocr_low_confidence_threshold: int = Field(default=55, ge=0, le=100)

    #: Local, non-generative OCR engine used by the adapter.
    ocr_engine: Literal["tesseract"] = "tesseract"
    ocr_language: str = "eng"

    #: Optional absolute path to the Tesseract executable. Leave empty to let
    #: pytesseract resolve it from PATH (/ the well-known install locations).
    ocr_tesseract_cmd: str = ""

    # --- Phase 3: access-code verification and amount comparison ---
    # Verification state also lives purely in process memory.

    #: Lifetime of one verification challenge, starting at identification time.
    verification_challenge_ttl_minutes: int = Field(default=5, ge=1, le=1440)

    #: Failed access-code attempts allowed per challenge before it locks.
    verification_max_attempts: int = Field(default=3, ge=1, le=10)

    #: PBKDF2 work factor for hashing the low-entropy fictional access codes.
    access_code_pbkdf2_iterations: int = Field(default=60_000, ge=1_000, le=1_000_000)

    # --- Phase 8: local GenAI bill explanation (Ollama, localhost only) ---

    #: Base URL of the local Ollama server. The explanation feature never
    #: talks to a cloud AI provider; the default keeps everything on the
    #: developer's own machine at the standard Ollama endpoint.
    ollama_base_url: str = "http://localhost:11434"

    #: Local model pulled with ``ollama pull`` (non-generative OCR stays
    #: Tesseract; this powers only the optional explanation layer).
    ollama_model: str = "qwen3:1.7b"

    #: Per-request timeout for the local model call. A slow/absent model never
    #: blocks the endpoint for long: responses degrade to deterministic text.
    ollama_timeout_seconds: float = Field(default=60.0, ge=5, le=600)

    #: Hard character ceiling for one generated explanation. Longer completions
    #: are discarded (never truncated silently) in favour of the fallback.
    ollama_max_output_chars: int = Field(default=2000, ge=200, le=8000)

    # --- Phase 9: grounded Q&A, personalised explanations, caregiver summaries ---
    # All conversation/rate-limit/caregiver state stays in process memory.

    #: Character ceiling for one follow-up question (also bounded by the
    #: request schema, so this only ever tightens the limit).
    ai_question_max_chars: int = Field(default=500, ge=20, le=1000)

    #: Follow-up questions one patient session may ask in total. Enforced by
    #: the backend on every request; clients cannot raise it.
    ai_questions_per_session: int = Field(default=10, ge=1, le=100)

    #: Character ceiling for one generated Q&A answer.
    ai_answer_max_chars: int = Field(default=800, ge=200, le=2000)

    #: Character ceiling for a personalised explanation ("short" mode uses
    #: half of this budget).
    personalized_max_chars: int = Field(default=900, ge=200, le=2000)

    #: Character ceiling for a caregiver summary rewrite.
    caregiver_summary_max_chars: int = Field(default=900, ge=200, le=2000)

    #: Lifetime of one caregiver share code. Must be re-minted afterwards.
    caregiver_share_ttl_minutes: int = Field(default=60, ge=5, le=1440)

    # --- Phase 4: staff support workflow ---

    #: Support-worker bearer token for the /api/v1/staff endpoints. Read from
    #: the environment variable SUPPORT_STAFF_API_TOKEN (no HBN_ prefix, wide
    #: default = empty, which makes every staff endpoint fail closed).
    support_staff_api_token: str = Field(
        default="", validation_alias="SUPPORT_STAFF_API_TOKEN"
    )

    @field_validator("support_staff_api_token")
    @classmethod
    def _validate_staff_token(cls, value: str) -> str:
        token = value.strip()
        if token and token.lower() in _PLACEHOLDER_TOKENS:
            # Never echo the configured value: placeholders are as unsafe as
            # no secret, so reject them explicitly (before any other rule).
            raise ValueError(
                "SUPPORT_STAFF_API_TOKEN must not be a well-known placeholder "
                "value. Configure a real, secret token instead."
            )
        if token and len(token) < 16:
            raise ValueError(
                "SUPPORT_STAFF_API_TOKEN must be at least 16 characters when set."
            )
        return token

    @property
    def bill_upload_max_size_bytes(self) -> int:
        """Upload ceiling in bytes, enforced while the request is being read."""

        return self.bill_upload_max_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        """Normalised CORS allow-list."""

        return parse_origin_list(self.cors_origins)

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors_origins(cls, value: str) -> str:
        return ", ".join(parse_origin_list(value))

    @field_validator("api_v1_prefix")
    @classmethod
    def _normalise_prefix(cls, value: str) -> str:
        prefix = "/" + value.strip().strip("/")
        if prefix == "/":
            raise ValueError("The API version prefix cannot be empty.")
        return prefix

    @field_validator("request_id_header")
    @classmethod
    def _validate_request_id_header(cls, value: str) -> str:
        header = value.strip()
        if not header or any(character.isspace() for character in header):
            raise ValueError("HBN_REQUEST_ID_HEADER must be a non-empty HTTP header name.")
        return header

    @field_validator("consent_policy_version")
    @classmethod
    def _validate_consent_policy_version(cls, value: str) -> str:
        version = value.strip()
        if not version:
            raise ValueError("HBN_CONSENT_POLICY_VERSION must be a non-empty policy version.")
        return version

    @field_validator("ollama_base_url")
    @classmethod
    def _validate_ollama_base_url(cls, value: str) -> str:
        base = value.strip().rstrip("/")
        if not base:
            raise ValueError("HBN_OLLAMA_BASE_URL must be a non-empty URL.")
        parts = urlsplit(base)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError(
                f"Invalid HBN_OLLAMA_BASE_URL {base!r}. "
                "Expected 'http://host[:port]' (the local Ollama server)."
            )
        if parts.query or parts.fragment:
            raise ValueError(
                f"Invalid HBN_OLLAMA_BASE_URL {base!r}. Query strings and "
                "fragments are not allowed."
            )
        return base

    @model_validator(mode="after")
    def _reject_wildcard_with_credentials(self) -> Settings:
        if self.cors_allow_credentials and "*" in self.cors_origins_list:
            raise ValueError(
                "HBN_CORS_ALLOW_CREDENTIALS cannot be true while HBN_CORS_ORIGINS "
                "contains '*'. List explicit frontend origins instead."
            )
        return self

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> Settings:
        """Fail deployment-fast when production mode ships unsafe defaults.

        Local development stays relaxed, but ``environment='production'`` must
        not silently inherit development-friendly defaults. Errors never echo
        configured secret values.
        """

        if self.environment != "production":
            return self
        if not self.support_staff_api_token:
            raise ValueError(
                "environment='production' requires SUPPORT_STAFF_API_TOKEN to be "
                "set so the support-worker endpoints cannot be left unsecured."
            )
        if tuple(self.cors_origins_list) == _DEV_DEFAULT_ORIGINS:
            raise ValueError(
                "environment='production' cannot use the development default "
                "CORS origins. Configure the real deployment origins in "
                "HBN_CORS_ORIGINS explicitly."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""

    return Settings()
