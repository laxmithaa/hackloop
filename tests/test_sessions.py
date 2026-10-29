"""Tests for patient sessions and consent endpoints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.services.session_store import SessionStore


async def _create_session(client: AsyncClient) -> dict:
    response = await client.post("/api/v1/sessions")
    assert response.status_code == 201
    return response.json()


async def test_create_session_returns_identifier_and_consent_state(
    client: AsyncClient,
) -> None:
    body = await _create_session(client)

    assert set(body) == {"session_id", "consent"}
    assert len(body["session_id"]) >= 20
    assert body["consent"] == {
        "recorded": False,
        "decision": None,
        "policy_version": None,
        "recorded_at": None,
    }


async def test_session_ids_are_unpredictable(client: AsyncClient) -> None:
    first = (await _create_session(client))["session_id"]
    second = (await _create_session(client))["session_id"]

    assert first != second


async def test_record_consent_and_state_is_server_validated(client: AsyncClient, app) -> None:
    body = await _create_session(client)
    session_id = body["session_id"]
    policy_version = app.state.settings.consent_policy_version

    response = await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={"decision": "granted", "policy_version": policy_version},
    )

    assert response.status_code == 200
    recorded = response.json()
    assert recorded["decision"] == "granted"
    assert recorded["policy_version"] == policy_version
    assert recorded["recorded_at"] is not None
    assert recorded["session_id"] == session_id


async def test_consent_with_outdated_policy_version_is_rejected(client: AsyncClient) -> None:
    session_id = (await _create_session(client))["session_id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={"decision": "granted", "policy_version": "consent-2019-v1"},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "consent_policy_outdated"
    assert error["message"]


async def test_consent_decision_must_be_granted_literal(client: AsyncClient) -> None:
    session_id = (await _create_session(client))["session_id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={"decision": "checked-the-checkbox", "policy_version": "anything"},
    )

    assert response.status_code == 422


async def test_withdraw_consent(client: AsyncClient) -> None:
    session_id = (await _create_session(client))["session_id"]

    response = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")

    assert response.status_code == 200
    assert response.json()["decision"] == "withdrawn"
    # Withdrawing again remains safe.
    again = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")
    assert again.status_code == 200


async def test_unknown_session_is_rejected_with_404(client: AsyncClient) -> None:
    unknown = "unknown-session-identifier-0123456789"

    consent = await client.post(
        f"/api/v1/sessions/{unknown}/consent",
        json={"decision": "granted", "policy_version": "x"},
    )
    withdraw = await client.post(f"/api/v1/sessions/{unknown}/consent/withdraw")

    for response in (consent, withdraw):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "session_not_found"


async def test_expired_session_is_rejected(client: AsyncClient, app) -> None:
    body = await _create_session(client)
    session_id = body["session_id"]
    # Force the session to be beyond the end of its validity window.
    store: SessionStore = app.state.session_store
    store._ttl = timedelta(0)

    response = await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={"decision": "granted", "policy_version": "x"},
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "session_expired"
    assert error["message"] == "This session has expired. Please start a new session."


def test_session_store_ttl_zero_expires_immediately() -> None:
    store = SessionStore(ttl_minutes=0)
    session = store.create()

    with pytest.raises(Exception) as exc_info:
        store.get(session.session_id)
    assert exc_info.value.code == "session_expired"
