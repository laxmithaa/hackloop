"""Tests for ``GET /health`` and ``GET /api/v1/health``."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.config import Settings


async def test_health_returns_success(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


async def test_health_response_structure(client: AsyncClient, settings: Settings) -> None:
    response = await client.get("/health")
    body = response.json()

    assert body["status"] == "ok"
    assert body["application"]["name"] == settings.app_name
    assert body["application"]["version"] == settings.app_version
    assert body["application"]["environment"] == "test"
    # The timestamp must be a valid timezone-aware UTC instant.
    parsed = datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))
    assert parsed.tzinfo is UTC
    assert set(body) == {"status", "application", "timestamp"}


async def test_versioned_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["application"]["name"]
