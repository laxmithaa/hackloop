"""Operational hardening and deployment-readiness tests (Phase 6).

Covers the configuration-safety and security-header protections that were
actually implemented:

- Placeholder staff tokens are rejected like missing ones.
- ``environment='production'`` refuses to ship with development-safe
  defaults (no staff token, localhost CORS origins).
- Conservative security response headers are stamped on every response
  without breaking the docs pages or request-id correlation.
- Public health responses stay minimal and secret-free.
- ``.env`` remains ignored by Git and the packaging hygiene holds.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings, get_settings
from app.main import create_application

#: ``BACKEND_DIR`` is the directory that contains ``app/`` — the project root.
PROJECT_ROOT = BACKEND_DIR


def make_settings(**overrides: object) -> Settings:
    """Build settings without reading the developer's local ``.env`` file."""

    return Settings(_env_file=None, **overrides)


# --- Configuration safety -------------------------------------------------------


@pytest.mark.parametrize("placeholder", ["changeme", "ChangeMe", "admin", "placeholder"])
def test_placeholder_staff_tokens_are_rejected(placeholder: str) -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        make_settings(support_staff_api_token=placeholder)


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": "production"},  # no staff token
        {"environment": "production", "cors_origins": "http://localhost:3000"},
    ],
)
def test_unsafe_production_combinations_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        make_settings(**overrides)


def test_production_with_explicit_safe_configuration_builds() -> None:
    settings = make_settings(
        environment="production",
        cors_origins="https://caregiver.example.test",
        support_staff_api_token="production-secret-token-000000000001",
    )

    assert settings.environment == "production"
    assert settings.support_staff_api_token  # value is kept, never printed


def test_invalid_production_configuration_fails_startup_understandably() -> None:
    with pytest.raises(ValidationError, match="SUPPORT_STAFF_API_TOKEN"):
        create_application(make_settings(environment="production"))


def test_local_development_keeps_working_without_a_staff_token() -> None:
    settings = make_settings()

    assert settings.environment == "local"
    assert settings.support_staff_api_token == ""  # staff endpoints fail closed


# --- Security response headers ---------------------------------------------------


async def test_security_headers_are_present_on_health_and_api_routes(
    app, client: AsyncClient
) -> None:
    for path in ("/health", "/api/v1/health"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"

    assert (await client.get("/docs")).status_code == 200


async def test_security_headers_are_present_on_error_responses(
    app, client: AsyncClient
) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    # Request-id correlation must survive the extra middleware.
    assert response.headers.get("x-request-id")


# --- Health responses and secrets -------------------------------------------------


async def test_health_response_stays_minimal_and_secret_free(
    app, client: AsyncClient
) -> None:
    response = await client.get("/health")
    body = response.json()
    assert set(body) == {"status", "application", "timestamp"}
    assert set(body["application"]) == {"name", "version", "environment"}
    assert body["status"] == "ok"
    serialised = response.text.lower()
    assert "token" not in serialised
    assert "secret" not in serialised
    assert "hbn_" not in serialised


def test_secret_values_never_reach_logs(app, caplog) -> None:
    import logging

    secret_token = "e2e-log-check-secret-token-0123456789"
    settings = make_settings(support_staff_api_token=secret_token)
    with caplog.at_level(logging.DEBUG):
        create_application(settings)

    joined = " ".join(record.getMessage() for record in caplog.records)
    assert secret_token not in joined


# --- Repository and dependency hygiene -------------------------------------------


def test_env_file_and_venv_remain_git_ignored() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert ".venv/" in gitignore
    assert "__pycache__/" in gitignore
    assert "*.log" in gitignore


def test_runtime_dependencies_are_pinned_exactly() -> None:
    text = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    runtime_prefixes = (
        "fastapi", "uvicorn", "pydantic", "httpx", "pillow",
        "pytesseract", "python-multipart", "python-dotenv",
        "pydantic-settings", "pytest", "pytest-asyncio", "ruff",
    )
    runtime_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(runtime_prefixes)
    ]
    assert runtime_lines, "requirements.txt must declare the runtime dependencies"
    for line in runtime_lines:
        assert "==" in line, f"unpinned dependency: {line!r}"


def test_get_settings_still_cached_after_hardening() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
