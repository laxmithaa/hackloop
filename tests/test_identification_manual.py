"""Tests for ``POST /api/v1/identifications`` (manual bill-number identification)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.records import (
    BILLS,
    HOSPITALS,
    BillRecord,
    HospitalRecord,
    InMemoryBillRecordAccess,
)

SAFE_RESPONSE_KEYS = {
    "identification_id",
    "status",
    "hospital_name",
    "bill_number",
    "message",
    "next_action",
}


async def _granted_session(client: AsyncClient, app) -> str:
    response = await client.post("/api/v1/sessions")
    session_id = response.json()["session_id"]
    await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={
            "decision": "granted",
            "policy_version": app.state.settings.consent_policy_version,
        },
    )
    return session_id


async def test_consent_is_required_before_identification(client: AsyncClient) -> None:
    response = await client.post("/api/v1/sessions")
    session_id = response.json()["session_id"]

    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )

    assert result.status_code == 403
    error = result.json()["error"]
    assert error["code"] == "consent_required"


async def test_unknown_session_is_rejected(client: AsyncClient) -> None:
    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": "unknown-session-identifier-0123", "bill_number": "SUN-2026-004512"},
    )

    assert result.status_code == 404
    assert result.json()["error"]["code"] == "session_not_found"


async def test_withdrawn_consent_blocks_identification(client: AsyncClient, app) -> None:
    session_id = await _granted_session(client, app)
    await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")

    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )

    assert result.status_code == 403
    assert result.json()["error"]["code"] == "consent_required"


async def test_registered_hospital_with_matching_bill_is_identified(
    client: AsyncClient, app
) -> None:
    session_id = await _granted_session(client, app)

    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )

    assert result.status_code == 200
    body = result.json()
    assert set(body) == SAFE_RESPONSE_KEYS
    assert body["status"] == "access_code_required"
    assert body["hospital_name"] == "Sunrise Multispeciality Hospital"
    assert body["bill_number"] == "SUN-2026-004512"
    assert body["next_action"] == "verify_access_code"
    assert body["identification_id"]


@pytest.mark.parametrize(
    ("bill_number", "hospital"),
    [
        ("sun. 2026 - 004512", None),  # spacing, capitalisation and punctuation noise
        ("SUN2026004512", None),  # no separators at all
        ("GME-2026-001122", "greenmeadow city"),  # hospital narrowing by partial name
        ("sun-2026-004512.", "  Sunrise Hospital!  "),  # hospital hint with noise
    ],
)
async def test_ocr_style_variations_still_identify(
    client: AsyncClient, app, bill_number: str, hospital: str | None
) -> None:
    session_id = await _granted_session(client, app)

    payload = {"session_id": session_id, "bill_number": bill_number}
    if hospital:
        payload["hospital_identifier"] = hospital
    result = await client.post("/api/v1/identifications", json=payload)

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "access_code_required", body
    assert body["next_action"] == "verify_access_code"


async def test_missing_bill_at_registered_hospital(client: AsyncClient, app) -> None:
    session_id = await _granted_session(client, app)

    result = await client.post(
        "/api/v1/identifications",
        json={
            "session_id": session_id,
            "bill_number": "SUN-2026-999999",
            "hospital_identifier": "Sunrise Hospital",
        },
    )

    assert result.status_code == 200
    body = result.json()
    assert set(body) == SAFE_RESPONSE_KEYS
    assert body["status"] == "bill_not_found"
    assert body["hospital_name"] == "Sunrise Multispeciality Hospital"
    assert body["next_action"] == "check_bill_number"


async def test_unregistered_hospital_is_reported_not_identified(client: AsyncClient, app) -> None:
    session_id = await _granted_session(client, app)

    result = await client.post(
        "/api/v1/identifications",
        json={
            "session_id": session_id,
            "bill_number": "SUN-2026-004512",
            "hospital_identifier": "Blue Lotus Wellness Center",
        },
    )

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "hospital_not_registered"
    assert body["next_action"] == "check_hospital_name"
    # No candidate hospital or bill may be implied.
    assert body["hospital_name"] is None
    assert body["bill_number"] is None


async def test_ambiguous_bill_number_asks_for_hospital(client: AsyncClient, app) -> None:
    hospital_a = HospitalRecord("hosp-city-a", "City Care Hospital", "CITY-A", ())
    hospital_b = HospitalRecord("hosp-city-b", "City Care Hospital West", "CITY-B", ())
    same_number = "CIT-2026-000001"
    bill_a = BillRecord(
        bill_id="bill-cit-000001-a",
        bill_number=same_number,
        hospital_id="hosp-city-a",
        bill_date="2026-04-01",
        total_amount_cents=100_000,
        patient_payable_cents=50_000,
    )
    bill_b = BillRecord(
        bill_id="bill-cit-000001-b",
        bill_number=same_number,
        hospital_id="hosp-city-b",
        bill_date="2026-04-02",
        total_amount_cents=200_000,
        patient_payable_cents=100_000,
    )
    app.state.records = InMemoryBillRecordAccess(
        hospitals=(hospital_a, hospital_b), bills=(bill_a, bill_b)
    )

    session_id = await _granted_session(client, app)
    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "CIT-2026-000001"},
    )

    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "ambiguous_hospital"
    assert body["next_action"] == "provide_hospital_identifier"


async def test_no_financial_information_is_returned(client: AsyncClient, app) -> None:
    session_id = await _granted_session(client, app)

    result = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )

    body = result.json()
    assert set(body) == SAFE_RESPONSE_KEYS
    text = result.text.lower()
    # The matched bill's fictional values must not appear anywhere.
    assert "12,480" not in text
    assert "6,240" not in text
    for banned_key in ("amount", "total", "due_date", "insurance", "payable", "charges"):
        assert banned_key not in set(body)


async def test_identification_record_keeps_candidates_server_side(client: AsyncClient, app) -> None:
    session_id = await _granted_session(client, app)
    await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )

    session = app.state.session_store.get(session_id)
    assert len(session.identifications) == 1
    assert session.identifications[0].status == "access_code_required"
    assert session.identifications[0].hospital_id == "hosp-sunrise"


async def test_missing_fields_return_422_envelope(client: AsyncClient, app) -> None:
    await _granted_session(client, app)

    response = await client.post("/api/v1/identifications", json={})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert {detail["field"] for detail in error["details"]} >= {
        "body.session_id",
        "body.bill_number",
    }


def test_registry_data_is_fictional_and_consistent() -> None:
    """Sanity check the bundled fictional data the API depends on."""

    registered = {hospital.hospital_id for hospital in HOSPITALS}
    assert len(registered) == 3
    assert all(bill.hospital_id in registered for bill in BILLS)
