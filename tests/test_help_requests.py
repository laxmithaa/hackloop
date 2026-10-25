"""Phase 4 tests: patient help requests, isolation, staff security, privacy.

Notes:
- All tests drive the API with the repository's ASGI client (no network).
- No real callback, SMS or email is ever attempted by these tests or by the
  application: Phase 4 only records workflow status.
- Patient free-text reasons and staff tokens never appear in responses that
  patients read or in log records.
"""

from __future__ import annotations

import json
import re

import pytest
from httpx import AsyncClient

from tests.conftest import create_consented_session, identify_bill

STAFF_TOKEN = "unit-test-staff-token-0123456789abcdef"
STAFF_HEADER = {"X-Support-Staff-Token": STAFF_TOKEN}

VALID_REASON = "I could not read the payable amount on my bill and need help."


def enable_staff(app, token: str = STAFF_TOKEN) -> None:
    app.state.settings.support_staff_api_token = token


def help_body(
    session_id: str,
    identification_id: str,
    *,
    reason: str = VALID_REASON,
    language: str = "mr",
    callback_window: str = "evening",
    consent: bool = True,
) -> dict:
    payload = {
        "session_id": session_id,
        "identification_id": identification_id,
        "language": language,
        "callback_window": callback_window,
        "reason": reason,
    }
    if consent:
        payload["consent_sharing_confirmed"] = True
    return payload


async def post_help(client: AsyncClient, body: dict):
    return await client.post(
        "/api/v1/help-requests",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )


async def create_ticket(
    client: AsyncClient, app, *, reason: str = VALID_REASON
) -> tuple[dict, str]:
    """Create one ticket; return ``(ticket_response, owning_session_id)``."""

    session_id = await create_consented_session(client)
    identification_id = await identify_bill(client, session_id)
    response = await post_help(
        client, help_body(session_id, identification_id, reason=reason)
    )
    assert response.status_code == 201, response.text
    return response.json(), session_id


# --- Creation and validation -------------------------------------------


async def test_valid_request_returns_ticket_id_and_new_status(
    app, client: AsyncClient
) -> None:
    created, _ = await create_ticket(client, app)
    assert created == {
        "ticket_id": created["ticket_id"],
        "status": "new",
        "language": "mr",
        "callback_window": "evening",
    }
    assert len(created["ticket_id"]) >= 16  # long, unpredictable ticket id


@pytest.mark.parametrize(
    "overrides",
    [
        {"consent": False},  # request body lacks explicit sharing consent
        {"language": "fr"},  # unsupported language
        {"language": ""},  # empty language string
        {"callback_window": "midnight"},  # not one of the four windows
        {"reason": ""},  # empty reason
        {"reason": "   \n "},  # whitespace-only reason
        {"reason": "abc"},  # below min length
        {"reason": "x" * 3000},  # oversized reason
    ],
)
async def test_invalid_request_fields_are_rejected_without_creating_a_ticket(
    app, client: AsyncClient, overrides: dict
) -> None:
    before = len(app.state.help_request_store)
    session_id = await create_consented_session(client)
    identification_id = await identify_bill(client, session_id)
    response = await post_help(
        client, help_body(session_id, identification_id, **overrides)
    )
    assert response.status_code == 422, response.text
    assert (
        len(app.state.help_request_store) == before
    ), "a rejected request must create no ticket"


async def test_unverified_bill_still_creates_help_request(app, client: AsyncClient) -> None:
    # No /verify call at all: asking for human help must not require it.
    created, _ = await create_ticket(client, app)
    assert created["status"] == "new"
    assert "amount" not in json.dumps(created).lower()
    assert "₹" not in json.dumps(created) and "rs." not in json.dumps(created).lower()


async def test_identification_of_another_session_is_rejected(
    app, client: AsyncClient
) -> None:
    session_a = await create_consented_session(client)
    session_b = await create_consented_session(client)
    identification_b = await identify_bill(client, session_b)

    response = await post_help(client, help_body(session_a, identification_b))
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "identification_not_found"


async def test_unknown_session_is_rejected(app, client: AsyncClient) -> None:
    response = await post_help(
        client,
        help_body("n0sUcHsEsSiOnIdxxxxxxxxxxxxxx1", "n0sUchIdentiFicAtion1"),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


async def test_withdrawn_session_consent_is_rejected(app, client: AsyncClient) -> None:
    session_id = await create_consented_session(client)
    await identify_bill(client, session_id)
    withdraw = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")
    assert withdraw.status_code == 200

    response = await post_help(
        client,
        help_body(session_id, "irrelevant"),
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "consent_required"


async def test_repeated_requests_create_distinct_tickets(app, client: AsyncClient) -> None:
    first, session_id = await create_ticket(client, app)
    identification_id = await identify_bill(client, session_id)
    second_response = await post_help(
        client, help_body(session_id, identification_id)
    )
    assert second_response.status_code == 201
    second = second_response.json()

    assert first["ticket_id"] != second["ticket_id"]


# --- Patient ticket access and cross-session isolation ------------------


async def test_patient_can_retrieve_own_ticket(app, client: AsyncClient) -> None:
    created, session_id = await create_ticket(client, app)
    response = await client.get(
        f"/api/v1/help-requests/{created['ticket_id']}",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    assert response.json() == created


async def test_other_session_cannot_retrieve_someone_elss_ticket(
    app, client: AsyncClient
) -> None:
    created, _ = await create_ticket(client, app)
    other_session = await create_consented_session(client)

    response = await client.get(
        f"/api/v1/help-requests/{created['ticket_id']}",
        headers={"X-Session-ID": other_session},
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "help_ticket_not_found"


async def test_unknown_ticket_uses_safe_error_format(app, client: AsyncClient) -> None:
    session_id = await create_consented_session(client)
    response = await client.get(
        "/api/v1/help-requests/deadbeefdeadbeefdeadbeefdeadbeef",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "help_ticket_not_found"
    assert error["request_id"]  # envelope keeps correlation id


async def test_withdrawn_sharing_hides_staff_view_but_patient_still_sees_status(
    app, client: AsyncClient
) -> None:
    enable_staff(app)
    created, session_id = await create_ticket(client, app)
    withdrawal = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")
    assert withdrawal.status_code == 200

    staff_list = await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)
    assert all(
        item["ticket_id"] != created["ticket_id"] for item in staff_list.json()
    )
    staff_detail = await client.get(
        f"/api/v1/staff/help-requests/{created['ticket_id']}", headers=STAFF_HEADER
    )
    assert staff_detail.status_code == 404

    patient_view = await client.get(
        f"/api/v1/help-requests/{created['ticket_id']}",
        headers={"X-Session-ID": session_id},
    )
    assert patient_view.status_code == 200
    assert patient_view.json()["status"] == "new"


# --- Support-worker security --------------------------------------------


async def test_staff_endpoints_fail_closed_when_token_not_configured(
    app, client: AsyncClient
) -> None:
    app.state.settings.support_staff_api_token = ""
    response = await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "support_staff_unavailable"
    assert isinstance(response.json()["error"]["message"], str)


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Support-Staff-Token": ""}, {"X-Support-Staff-Token": "wrong-token-value"}],
)
async def test_missing_or_incorrect_staff_token_is_rejected(
    app, client: AsyncClient, headers: dict
) -> None:
    enable_staff(app)
    await create_ticket(client, app)
    response = await client.get("/api/v1/staff/help-requests", headers=headers)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "support_staff_unauthorized"


async def test_staff_listing_hides_withdrawn_and_unconsented_tickets(
    app, client: AsyncClient
) -> None:
    enable_staff(app)
    visible, _ = await create_ticket(client, app)
    withdrawn, withdrawn_session = await create_ticket(client, app)
    await client.post(f"/api/v1/sessions/{withdrawn_session}/consent/withdraw")

    response = await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)
    assert response.status_code == 200
    listed_ids = [item["ticket_id"] for item in response.json()]
    assert listed_ids == [visible["ticket_id"]]
    assert withdrawn["ticket_id"] not in listed_ids


async def test_staff_detail_contains_reason_and_summary(app, client: AsyncClient) -> None:
    enable_staff(app)
    reason = "Verification failed twice and the amounts look doubled."
    created, _ = await create_ticket(client, app, reason=reason)
    response = await client.get(
        f"/api/v1/staff/help-requests/{created['ticket_id']}", headers=STAFF_HEADER
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["reason"] == reason
    assert "not_verified" in detail["summary"]
    assert "not treat the bill" in detail["summary"]
    # No monetary *values* anywhere in the staff detail (the word "amount"
    # may legitimately appear in the patient's verbatim reason or the fixed
    # template, but no currency figure does).
    money_pattern = re.compile(r"(?:₹|rs\.\s*)\s*\d|\d{1,3}(?:,\d{3})+\.\d{2}")
    assert not money_pattern.search(json.dumps(detail))


async def test_staff_status_transitions_follow_the_state_machine(
    app, client: AsyncClient
) -> None:
    enable_staff(app)
    created, _ = await create_ticket(client, app)
    ticket_id = created["ticket_id"]
    base = f"/api/v1/staff/help-requests/{ticket_id}/status"

    scheduled = await client.post(
        base, json={"status": "callback_scheduled"}, headers=STAFF_HEADER
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["status"] == "callback_scheduled"

    contacted = await client.post(
        base, json={"status": "contacted"}, headers=STAFF_HEADER
    )
    assert contacted.status_code == 200

    resolved = await client.post(
        base, json={"status": "resolved"}, headers=STAFF_HEADER
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    # resolved is terminal
    after = await client.post(
        base, json={"status": "contacted"}, headers=STAFF_HEADER
    )
    assert after.status_code == 409
    assert after.json()["error"]["code"] == "invalid_status_transition"


async def test_backward_transitions_and_unknown_statuses_are_rejected(
    app, client: AsyncClient
) -> None:
    enable_staff(app)
    created, _ = await create_ticket(client, app)
    base = f"/api/v1/staff/help-requests/{created['ticket_id']}/status"

    scheduled = await client.post(
        base, json={"status": "callback_scheduled"}, headers=STAFF_HEADER
    )
    assert scheduled.status_code == 200

    backward = await client.post(
        base, json={"status": "new"}, headers=STAFF_HEADER
    )
    assert backward.status_code == 409

    unknown = await client.post(
        base, json={"status": "archived"}, headers=STAFF_HEADER
    )
    assert unknown.status_code == 422


# --- Privacy, logs and regressions ---------------------------------------


async def test_patient_responses_expose_no_amounts_or_codes(
    app, client: AsyncClient
) -> None:
    created, session_id = await create_ticket(client, app)
    own = await client.get(
        f"/api/v1/help-requests/{created['ticket_id']}",
        headers={"X-Session-ID": session_id},
    )
    text = json.dumps(own.json()).lower()
    assert "₹" not in text and "rs." not in text and "amount" not in text


async def test_logs_contain_no_reason_text(app, client: AsyncClient, caplog) -> None:
    import logging

    secret_reason = "unicorn-reason-7d9f2b must never be logged"
    enable_staff(app)
    with caplog.at_level(logging.DEBUG, logger="app"):
        created, _ = await create_ticket(client, app, reason=secret_reason)
        await client.get(
            f"/api/v1/help-requests/{created['ticket_id']}",
            headers={"X-Session-ID": "whatever-not-needed"},
        )
        await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)

    joined = " ".join(record.getMessage() for record in caplog.records)
    assert secret_reason not in joined


async def test_openapi_schemas_expose_no_tokens(app, client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    schema_text = json.dumps(schema)
    assert STAFF_TOKEN not in schema_text
    paths = schema["paths"]
    for path in ("/api/v1/help-requests", "/api/v1/staff/help-requests"):
        assert path in paths


async def test_phase_4_adds_no_network_or_messaging_calls(app, client: AsyncClient) -> None:
    # The workflow records status only; the app and tests never contact
    # external services. As a structural guard, assert no such client exists
    # on the application state.
    assert not hasattr(app.state, "sms_client")
    assert not hasattr(app.state, "calls_client")
    assert not hasattr(app.state, "email_client")
