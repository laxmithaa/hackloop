"""Tests for environment-driven configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def make_settings(**overrides: object) -> Settings:
    """Build settings without reading the developer's local ``.env`` file."""

    return Settings(_env_file=None, **overrides)


def test_defaults_are_safe_for_local_development() -> None:
    settings = make_settings()

    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.request_id_header == "X-Request-ID"
    assert settings.app_version
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HBN_ENVIRONMENT", "staging")
    monkeypatch.setenv("HBN_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "HBN_CORS_ORIGINS", " https://app.example.test , https://admin.example.test/ "
    )

    settings = make_settings()

    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins_list == [
        "https://app.example.test",
        "https://admin.example.test",
    ]


def test_cors_origins_accept_a_json_array() -> None:
    settings = make_settings(
        cors_origins='["http://localhost:3000", "https://caregiver.example.test"]'
    )

    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://caregiver.example.test",
    ]


def test_invalid_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Invalid CORS origin"):
        make_settings(cors_origins="localhost:3000")


def test_wildcard_origin_with_credentials_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HBN_CORS_ALLOW_CREDENTIALS"):
        make_settings(cors_origins="*", cors_allow_credentials=True)


def test_wildcard_origin_is_allowed_without_credentials() -> None:
    settings = make_settings(cors_origins="*", cors_allow_credentials=False)

    assert settings.cors_origins_list == ["*"]


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(environment="unknown-env")


def test_unknown_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(log_level="VERBOSE")


def test_api_prefix_is_normalised() -> None:
    assert make_settings(api_v1_prefix="api/v2/").api_v1_prefix == "/api/v2"

    with pytest.raises(ValidationError):
        make_settings(api_v1_prefix="/")


def test_invalid_request_id_header_is_rejected() -> None:
    with pytest.raises(ValidationError, match="HBN_REQUEST_ID_HEADER"):
        make_settings(request_id_header="X Request ID")


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    try:
        first = get_settings()
        second = get_settings()

        assert isinstance(first, Settings)
        assert first is second
    finally:
        get_settings.cache_clear()
