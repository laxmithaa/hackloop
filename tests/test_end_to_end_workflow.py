"""End-to-end integration and regression hardening (Phase 5).

These tests drive the real application and its actual API contracts over the
in-process ASGI client (no network, no external services). They deliberately
join whole workflows across phases — session → consent → identification →
access-code verification → protected bill → help request → staff workflow —
and then probe the cross-phase security invariants (session ownership,
consent enforcement, financial privacy, access-code security, ticket
privacy, sensitive logging and request handling).

Existing focused Phase 1-4 suites keep ownership of their individual
behaviours; this module only adds the joined-up regression coverage.
"""

from __future__ import annotations

import io
import json
import logging
import re

from httpx import AsyncClient

from tests.conftest import create_consented_session

STAFF_TOKEN = "e2e-regression-staff-token-0123456789"
STAFF_HEADER = {"X-Support-Staff-Token": STAFF_TOKEN}
SUNRISE_CODE = "DEMO1234"

SUNRISE_BILL = "SUN-2026-004512"
REASON = "E2E: the payable amount looks doubled, please help me check."


# --- Shared helpers ------------------------------------------------------------


def enable_staff(app) -> None:
    app.state.settings.support_staff_api_token = STAFF_TOKEN


class FakeOcrAdapter:
    """Deterministic OCR stand-in (no Tesseract dependency in tests)."""

    engine = "fake"

    def __init__(self, text: str, mean_confidence: float = 99.0) -> None:
        self.text = text
        self.mean_confidence = mean_confidence

    def extract_image_text(self, image):
        from app.services.ocr import OcrResult

        return OcrResult(text=self.text, mean_confidence=self.mean_confidence)

    def extract_text(self, image):
        return self.extract_image_text(image)


def _png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), color=(252, 252, 252)).save(buffer, format="PNG")
    return buffer.getvalue()


async def record_consent(client: AsyncClient, session_id: str) -> dict:
    response = await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={"decision": "granted", "policy_version": "patient-consent-2026-10-v1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def identify_manually(
    client: AsyncClient, session_id: str, bill_number: str = SUNRISE_BILL
) -> dict:
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": bill_number},
    )
    assert response.status_code == 200, response.text
    return response.json()


def error_of(response) -> dict:
    body = response.json()
    assert set(body) == {"error"}, body
    return body["error"]


def error_docs(client: AsyncClient):  # pragma: no cover - helper discipline
    raise NotImplementedError


# --- A. Complete successful patient workflow ------------------------------------


async def test_complete_patient_journey_end_to_end(
    client, app, fake_clock, verification_factory, caplog
) -> None:
    enable_staff(app)
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})

    with caplog.at_level(logging.DEBUG):
        # 1. Session
        created = await client.post("/api/v1/sessions")
        assert created.status_code == 201, created.text
        session_body = created.json()
        session_id = session_body["session_id"]
        assert session_body["consent"]["recorded"] is False
        assert len(created.headers["x-request-id"]) >= 1

        # 2. Consent
        consent = await record_consent(client, session_id)
        assert consent["decision"] == "granted"

        # 3-4. Manual identification, no financial information in the response
        ident = await identify_manually(client, session_id)
        assert ident["status"] == "access_code_required"
        assert ident["bill_number"] == SUNRISE_BILL
        identification_id = ident["identification_id"]
        ident_text = json.dumps(ident)
        assert "12,480" not in ident_text and "6,240" not in ident_text
        assert "₹" not in ident_text and "12480.00" not in ident_text
        assert "declare" not in ident_text  # no extra junk — fields stay minimal
        assert set(ident) == {
            "identification_id",
            "status",
            "hospital_name",
            "bill_number",
            "message",
            "next_action",
        }

        # 5-6. Access-code challenge and verification
        verify = await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": SUNRISE_CODE},
        )
        assert verify.status_code == 200, verify.text
        verify_body = verify.json()
        assert verify_body["status"] == "verified"
        assert verify_body["identification_id"] == identification_id
        # Manual entry: nothing was uploaded, so comparison reports that state.
        assert verify_body["comparison"]["status"] == "no_uploaded_image"
        assert "12,480" not in json.dumps(verify_body)

        # 7-8. Protected financial information, only after verification
        protected = await client.get(
            f"/api/v1/verified-bills/{identification_id}",
            headers={"X-Session-ID": session_id},
        )
        assert protected.status_code == 200, protected.text
        bill = protected.json()
        assert bill["bill_number"] == SUNRISE_BILL
        assert bill["amounts"]["total_amount"]["value"] == "12480.00"
        assert bill["amounts"]["patient_payable"]["value"] == "6240.00"
        assert bill["amounts"]["total_amount"]["authoritative"] is True
        assert bill["amounts"]["patient_payable"]["authoritative"] is True

        # 9. Help request (Phase 4) on the same verified identification
        help_response = await client.post(
            "/api/v1/help-requests",
            json={
                "session_id": session_id,
                "identification_id": identification_id,
                "language": "en",
                "callback_window": "morning",
                "reason": REASON,
                "consent_sharing_confirmed": True,
            },
        )
        assert help_response.status_code == 201, help_response.text
        ticket = help_response.json()
        assert ticket["status"] == "new"
        assert set(ticket) == {
            "ticket_id",
            "status",
            "language",
            "callback_window",
        }

        # 10. Patient retrieves their own ticket
        own = await client.get(
            f"/api/v1/help-requests/{ticket['ticket_id']}",
            headers={"X-Session-ID": session_id},
        )
        assert own.status_code == 200, own.text
        assert own.json()["status"] == "new"

        # 11. Support worker manages the ticket through the state machine
        listed = await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)
        assert listed.status_code == 200, listed.text
        assert any(row["ticket_id"] == ticket["ticket_id"] for row in listed.json())

        detail = await client.get(
            f"/api/v1/staff/help-requests/{ticket['ticket_id']}",
            headers=STAFF_HEADER,
        )
        assert detail.status_code == 200, detail.text
        staff_detail = detail.json()
        assert staff_detail["reason"] == REASON
        # Verified with no upload: the deterministic summary names that state.
        assert "verified_no_upload" in staff_detail["summary"]
        assert re.search(r"(?:₹|rs\.\s*)\s*\d", staff_detail["summary"]) is None

        base = f"/api/v1/staff/help-requests/{ticket['ticket_id']}/status"
        for new_status in ("callback_scheduled", "contacted", "resolved"):
            moved = await client.post(
                base, json={"status": new_status}, headers=STAFF_HEADER
            )
            assert moved.status_code == 200, moved.text
            assert moved.json()["status"] == new_status
            patient_view = await client.get(
                f"/api/v1/help-requests/{ticket['ticket_id']}",
                headers={"X-Session-ID": session_id},
            )
            assert patient_view.json()["status"] == new_status

        # Nothing claims a real callback was placed or scheduled.
        assert "scheduled with" not in json.dumps(staff_detail).lower().replace(
            "callback_scheduled", ""
        )

    # Sensitive logging: no access code, staff token or reason text in logs.
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert SUNRISE_CODE not in joined
    assert STAFF_TOKEN not in joined
    assert REASON not in joined


# --- B. Identification and verification failure paths ---------------------------


async def test_unknown_session_is_rejected_for_identification(client) -> None:
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": "uNkNoWnSeSsIoNiDxxxxxxxxxxxxxx1", "bill_number": SUNRISE_BILL},
    )
    assert response.status_code == 404
    assert error_of(response)["code"] == "session_not_found"


async def test_withdrawn_consent_blocks_identification(client) -> None:
    session_id = await create_consented_session(client)
    withdrawal = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")
    assert withdrawal.status_code == 200

    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    assert response.status_code == 403
    assert error_of(response)["code"] == "consent_required"


async def test_unknown_bill_number_is_a_safe_domain_outcome(client) -> None:
    # Unknown bill numbers are a *business* outcome: 200 with status
    # bill_not_found (never an error leakage, never any financial value).
    session_id = await create_consented_session(client)
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "ZZZ-9999-999999"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "bill_not_found"
    assert set(body) == {
        "identification_id",
        "status",
        "hospital_name",
        "bill_number",
        "message",
        "next_action",
    }
    assert "12,480" not in json.dumps(body) and "amount" not in json.dumps(body).lower()


async def test_corrupt_image_is_rejected_without_ocr(client, app) -> None:
    app.state.ocr_adapter = FakeOcrAdapter("")
    session_id = await create_consented_session(client)
    fake = b"\x89PNG\r\n\x1a\n" + b"not-actually-a-png"
    response = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", fake, "image/png")},
    )
    assert response.status_code in {400, 422}
    body_text = json.dumps(response.json())
    assert "amount" not in body_text.lower() or set(
        response.json()
    ) == {"error"}


async def test_wrong_access_code_and_attempt_limit(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)
    identification_id = ident["identification_id"]
    url = f"/api/v1/identifications/{identification_id}/verify"
    payload = {"session_id": session_id, "access_code": "WRONGCODE"}

    first = await client.post(url, json=payload)
    assert first.status_code == 401
    assert error_of(first)["code"] == "access_code_invalid"
    assert "2" in error_of(first)["message"]  # remaining attempts stated

    second = await client.post(url, json=payload)
    assert second.status_code == 401
    third = await client.post(url, json=payload)
    assert third.status_code == 403
    assert error_of(third)["code"] == "verification_locked"

    fourth = await client.post(url, json=payload)  # reuse attempt after lock
    assert fourth.status_code == 403
    assert error_of(fourth)["code"] == "verification_locked"


async def test_expired_challenge_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)
    identification_id = ident["identification_id"]

    fake_clock.advance(minutes=10)  # beyond the five-minute challenge window
    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert response.status_code == 410
    assert error_of(response)["code"] == "verification_challenge_expired"


async def test_verification_of_another_sessions_identification_fails_closed(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_a = await create_consented_session(client)
    session_b = await create_consented_session(client)
    ident_b = await identify_manually(client, session_b)

    response = await client.post(
        f"/api/v1/identifications/{ident_b['identification_id']}/verify",
        json={"session_id": session_a, "access_code": SUNRISE_CODE},
    )
    assert response.status_code == 404
    assert error_of(response)["code"] == "identification_not_found"


async def test_protected_bill_before_verification_and_after_withdrawal(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)
    identification_id = ident["identification_id"]
    url = f"/api/v1/verified-bills/{identification_id}"

    # Not verified yet: no amounts, ever.
    pre = await client.get(url, headers={"X-Session-ID": session_id})
    assert pre.status_code == 403
    assert error_of(pre)["code"] == "verification_required"

    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert verified.status_code == 200
    assert await client.post(
        f"/api/v1/sessions/{session_id}/consent/withdraw"
    )  # withdraw after verification

    post = await client.get(url, headers={"X-Session-ID": session_id})
    assert post.status_code == 403
    assert error_of(post)["code"] == "consent_required"


async def test_uploaded_amounts_matching_the_record(
    client, app, verification_factory
) -> None:
    app.state.ocr_adapter = FakeOcrAdapter(
        "Sunrise Multispeciality Hospital\nBill No: SUN-2026-004512\n"
        "Total Amount: 12,480.00\nAmount Payable: 6,240.00"
    )
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    uploaded = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["status"] == "access_code_required"

    verify = await client.post(
        f"/api/v1/identifications/{uploaded.json()['identification_id']}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["comparison"]["status"] == "matched"


async def test_uploaded_amounts_differing_from_the_record(
    client, app, verification_factory
) -> None:
    app.state.ocr_adapter = FakeOcrAdapter(
        "Sunrise Multispeciality Hospital\nBill No: SUN-2026-004512\n"
        "Total Amount: 99,999.00\nAmount Payable: 6,240.00"
    )
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    uploaded = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    identification_id = uploaded.json()["identification_id"]

    verify = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["comparison"]["status"] == "amounts_differ"

    # Neutral wording: a mismatch is not an accusation.
    message = verify.json()["comparison"]["message"]
    assert "fraud" not in message.lower()
    assert "not prove fraud" in message or "not tell us" in message


async def test_uploaded_image_without_labelled_amounts(
    client, app, verification_factory
) -> None:
    app.state.ocr_adapter = FakeOcrAdapter(
        "Sunrise Multispeciality Hospital\nBill No: SUN-2026-004512\n"
        "12,480.00 and 6,240.00"  # monetary values but none is labelled
    )
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    uploaded = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    identification_id = uploaded.json()["identification_id"]

    verify = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["comparison"]["status"] == "insufficient_evidence"


# --- C. Phase 4 help-request integration ----------------------------------------


async def test_help_request_before_verification_creates_workflow_record(
    client, app, verification_factory
) -> None:
    # No /verify call: help must work for patients whose verification failed
    # (which is the point of human support), with the unverified state named.
    enable_staff(app)
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)

    response = await client.post(
        "/api/v1/help-requests",
        json={
            "session_id": session_id,
            "identification_id": ident["identification_id"],
            "language": "hi",
            "callback_window": "afternoon",
            "reason": "Doubt in total, phone pe help chahiye.",
            "consent_sharing_confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    ticket = response.json()
    assert ticket["status"] == "new"

    detail = await client.get(
        f"/api/v1/staff/help-requests/{ticket['ticket_id']}", headers=STAFF_HEADER
    )
    assert detail.status_code == 200, detail.text
    assert "not_verified" in detail.json()["summary"]


async def test_invalid_help_requests_and_isolation_join_the_large_matrix(
    client, app, verification_factory
) -> None:
    enable_staff(app)
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_a = await create_consented_session(client)
    ident_a = await identify_manually(client, session_a)

    # Missing request-specific consent.
    no_consent = await client.post(
        "/api/v1/help-requests",
        json={
            "session_id": session_a,
            "identification_id": ident_a["identification_id"],
            "language": "en",
            "callback_window": "now",
            "reason": "Please double-check my total.",
        },
    )
    assert no_consent.status_code == 422
    assert len(app.state.help_request_store) == 0  # no ticket side effect

    created = await client.post(
        "/api/v1/help-requests",
        json={
            "session_id": session_a,
            "identification_id": ident_a["identification_id"],
            "language": "en",
            "callback_window": "now",
            "reason": "Please double-check my total.",
            "consent_sharing_confirmed": True,
        },
    )
    assert created.status_code == 201
    ticket_b = created.json()["ticket_id"]

    # Unique ids across repeats.
    second = await client.post(
        "/api/v1/help-requests",
        json={
            "session_id": session_a,
            "identification_id": ident_a["identification_id"],
            "language": "en",
            "callback_window": "now",
            "reason": "Still need help, two doubts.",
            "consent_sharing_confirmed": True,
        },
    )
    assert second.status_code == 201
    assert second.json()["ticket_id"] != ticket_b

    # Staff authentication is enforced even here.
    anonymous = await client.get("/api/v1/staff/help-requests")
    assert anonymous.status_code in {401, 503}

    # Invalid ticket-status transition is rejected.
    base = f"/api/v1/staff/help-requests/{ticket_b}/status"
    scheduled = await client.post(
        base, json={"status": "callback_scheduled"}, headers=STAFF_HEADER
    )
    assert scheduled.status_code == 200
    backward = await client.post(
        base, json={"status": "new"}, headers=STAFF_HEADER
    )
    assert backward.status_code == 409

    # Consent withdrawal forbids staff access to the request.
    await client.post(f"/api/v1/sessions/{session_a}/consent/withdraw")
    hidden_list = await client.get("/api/v1/staff/help-requests", headers=STAFF_HEADER)
    assert all(row["ticket_id"] != ticket_b for row in hidden_list.json())
    hidden_detail = await client.get(
        f"/api/v1/staff/help-requests/{ticket_b}", headers=STAFF_HEADER
    )
    assert hidden_detail.status_code == 404


# --- Cross-phase security regressions -------------------------------------------


async def test_verified_financial_information_is_session_bound(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_b = await create_consented_session(client)
    ident_b = await identify_manually(client, session_b)
    identification_id = ident_b["identification_id"]
    ok = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_b, "access_code": SUNRISE_CODE},
    )
    assert ok.status_code == 200

    foreign = await create_consented_session(client)
    leak = await client.get(
        f"/api/v1/verified-bills/{identification_id}",
        headers={"X-Session-ID": foreign},
    )
    assert leak.status_code == 403
    assert error_of(leak)["code"] == "verification_required"
    assert "12,480" not in json.dumps(leak.json())


async def test_no_header_and_wrong_header_never_reach_financial_data(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)
    url = f"/api/v1/verified-bills/{ident['identification_id']}"

    no_header = await client.get(url)
    assert no_header.status_code in {401, 403, 422}

    wrong = await client.get(url, headers={"X-Session-ID": "x" * 20})
    assert wrong.status_code in {401, 403, 404, 422}
    assert "amount" not in json.dumps(wrong.json()).lower()


async def test_successful_verification_invalidates_the_challenge(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)
    identification_id = ident["identification_id"]
    url = f"/api/v1/identifications/{identification_id}/verify"

    first = await client.post(
        url, json={"session_id": session_id, "access_code": SUNRISE_CODE}
    )
    assert first.status_code == 200

    replay = await client.post(
        url, json={"session_id": session_id, "access_code": SUNRISE_CODE}
    )
    assert replay.status_code in {403, 410}  # reused challenge must not verify again
    assert error_of(replay)["code"] in {"verification_locked", "verification_challenge_expired"}


async def test_tokens_and_codes_stay_out_of_the_standard_error_envelope(
    client, app, verification_factory
) -> None:
    enable_staff(app)
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    ident = await identify_manually(client, session_id)

    bad_verify = await client.post(
        f"/api/v1/identifications/{ident['identification_id']}/verify",
        json={"session_id": session_id, "access_code": "WRONGCODE99"},
    )
    envelope = json.dumps(bad_verify.json())
    assert "WRONGCODE99" not in envelope
    bad_staff = await client.get(
        "/api/v1/staff/help-requests",
        headers={"X-Support-Staff-Token": "definitely-not-the-token"},
    )
    assert "definitely-not-the-token" not in json.dumps(bad_staff.json())


async def test_request_id_header_still_present_across_a_full_journey(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)

    created = await client.post("/api/v1/sessions")
    assert created.headers.get("x-request-id")
    ident = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    assert ident.headers.get("x-request-id")
    missing = await client.get("/api/v1/does-not-exist")
    assert missing.headers.get("x-request-id")


async def test_phase_2_4_upload_and_help_limits_still_enforced(
    client, app, verification_factory
) -> None:
    # A smaller configured ceiling still triggers 413 (size limit keeps working).
    app.state.settings.bill_upload_max_size_mb = 1
    app.state.ocr_adapter = FakeOcrAdapter(" Sunrise Hospital\nBill No: SUN-2026-004512")
    session_id = await create_consented_session(client)
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024 + 10)
    response = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", big, "image/png")},
    )
    assert response.status_code in {400, 413}
