"""Tests for application construction and startup/shutdown handling."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.main import app, create_application


def test_default_application_instance_is_built() -> None:
    """The module-level ``app`` exposes the expected FastAPI metadata."""

    assert isinstance(app, FastAPI)
    assert app.title == "Healthcare Bill Navigator API"
    assert app.version
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
    # The entry point uses the environment-derived settings.
    assert app.state.settings is get_settings()


async def test_lifespan_runs_startup_and_shutdown_events(lifespan_app) -> None:
    """Startup/shutdown handlers run without error through the full lifespan."""

    response = await lifespan_app.get("/health")

    assert response.status_code == 200


def test_create_application_builds_isolated_instances(settings) -> None:
    isolated = create_application(settings)
    assert isolated is not app
    assert isolated.state.settings is settings
    assert isolated.title == settings.app_name
