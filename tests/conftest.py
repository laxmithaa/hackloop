"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_application


class FakeClock:
    """Injectable clock for deterministic expiry tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 10, 25, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **delta) -> datetime:
        self._now += timedelta(**delta)
        return self._now

ClientFactory = Callable[[FastAPI], AsyncClient]


@pytest.fixture
def settings() -> Settings:
    """Isolated settings that never read the developer's local ``.env`` file."""

    return Settings(
        _env_file=None,
        environment="test",
        cors_origins="http://localhost:3000",
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    """Application instance built from the isolated settings."""

    return create_application(settings)


@pytest.fixture
def client_factory() -> ClientFactory:
    """Factory for HTTPX clients that never re-raise server exceptions.

    ``raise_app_exceptions=False`` lets tests assert on the 500 response body
    produced by the global exception handler.
    """

    def factory(application: FastAPI) -> AsyncClient:
        return AsyncClient(
            transport=ASGITransport(app=application, raise_app_exceptions=False),
            base_url="http://testserver",
        )

    return factory


@pytest.fixture
async def client(app: FastAPI, client_factory: ClientFactory) -> AsyncIterator[AsyncClient]:
    async with client_factory(app) as http_client:
        yield http_client


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def verification_factory(app: FastAPI, fake_clock: FakeClock):
    """Build a deterministic VerificationService on the isolated app.

    ``codes`` maps bill ids to plain codes (hashed here with a fixed salt so
    tests never depend on real environment provisioning).
    """

    from app.services.access_codes import hash_access_code
    from app.services.verification import VerificationService

    def factory(codes: dict[str, str] | None = None, *, max_attempts: int = 3):
        digests = {
            bill_id: hash_access_code(
                code, iterations=1000, salt=b"unit-test-fixed-salt-01"[:16]
            )
            for bill_id, code in (codes or {}).items()
        }
        service = VerificationService.build(
            records=app.state.records,
            session_store=app.state.session_store,
            digests=digests,
            challenge_ttl_minutes=5,
            max_attempts=max_attempts,
            now_fn=fake_clock,
        )
        app.state.verification_service = service
        return service

    return factory


async def create_consented_session(client: AsyncClient) -> str:
    import json as _json

    response = await client.post("/api/v1/sessions")
    session_id = response.json()["session_id"]
    await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        content=_json.dumps(
            {
                "decision": "granted",
                "policy_version": "patient-consent-2026-10-v1",
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    return session_id


async def identify_bill(
    client: AsyncClient, session_id: str, bill_number: str = "SUN-2026-004512"
) -> str:
    import json as _json

    response = await client.post(
        "/api/v1/identifications",
        content=_json.dumps({"session_id": session_id, "bill_number": bill_number}),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "access_code_required"
    return response.json()["identification_id"]


@pytest.fixture
async def lifespan_app(app: FastAPI, client_factory: ClientFactory) -> Iterator[AsyncClient]:
    """Run the application lifespan around a client session.

    httpx's ASGITransport does not trigger startup/shutdown, so tests that need
    lifespan behaviour drive it explicitly.
    """

    async with app.router.lifespan_context(app), client_factory(app) as http_client:
        yield http_client
