"""Access-code verification and protected-information tests.

Covers the acceptance list: correct/incorrect codes, attempt limiting and
concurrency, challenge and session expiry, unrelated sessions, withdrawn
consent, challenge reuse — and the privacy invariant that no financial field
(and no access code) escapes into any response or log before successful
verification.
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.identification import STATUS_ACCESS_CODE_REQUIRED
from tests.conftest import create_consented_session

# --- Test helpers -------------------------------------------------------------


def _error(body: dict[str, Any]) -> dict[str, Any]:
    """Return the ``error`` object of the standard error envelope."""

    assert set(body) == {"error"}, body
    return body["error"]


async def _start_verified(
    client,
    verification_factory,
    *,
    owner_session=True,
) -> tuple[str, str]:
    """Consented session + manual identification of the sunrise bill.

    The verification service must be installed on the app *before* the
    identification happens (challenges are created at identification time).
    """

    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    session_id = await create_consented_session(client)
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == STATUS_ACCESS_CODE_REQUIRED
    return body["identification_id"], session_id


def _png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), color=(250, 250, 250)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeOcrAdapter:
    """Deterministic OCR stand-in returning a fixed text."""

    engine = "fake"

    def __init__(self, text: str, mean_confidence: float = 99.0) -> None:
        self.text = text
        self.mean_confidence = mean_confidence

    def extract_image_text(self, image):
        from app.services.ocr import OcrResult

        return OcrResult(text=self.text, mean_confidence=self.mean_confidence)

    def extract_text(self, image):
        return self.extract_image_text(image)


# --- Verification outcomes -----------------------------------------------------


async def test_correct_access_code_verifies(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "verified"
    assert body["identification_id"] == identification_id


async def test_incorrect_access_code_shows_one_attempt_consumed(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "WRONGCODE"},
    )

    assert response.status_code == 401
    error = _error(response.json())
    assert error["code"] == "access_code_invalid"
    # Two attempts left; the remaining budget is stated, nothing else leaks.
    assert "2" in error["message"]


async def test_three_consecutive_failures_lock_the_verification(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    statuses = []
    for wrong_code in ("WRONG-A", "WRONG-B", "WRONG-C"):
        response = await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": wrong_code},
        )
        statuses.append(response.status_code)

    fourth = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert statuses == [401, 401, 403]
    assert fourth.status_code == 403
    assert _error(fourth.json())["code"] == "verification_locked"


async def test_expired_challenge_rejects_even_the_correct_code(
    client, app, fake_clock, verification_factory
) -> None:
    """Five minutes after identification the correct code is also refused."""

    identification_id, session_id = await _start_verified(client, verification_factory)
    fake_clock.advance(minutes=5, seconds=1)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert response.status_code == 410
    assert _error(response.json())["code"] == "verification_challenge_expired"


async def test_locked_challenge_cannot_be_reused_after_lockout(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    for wrong_code in ("WRONG-A", "WRONG-B", "WRONG-C"):
        await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": wrong_code},
        )

    # Even the correct code is refused while the challenge is locked.
    locked = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert locked.status_code == 403

    # Advancing time beyond the challenge window still refuses reuse.
    fake_clock.advance(minutes=6)
    stale = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert stale.status_code in {403, 410}


async def test_challenge_is_consumed_after_successful_verification(
    client, app, fake_clock, verification_factory
) -> None:
    """Success invalidates the challenge and re-verifying needs a new one."""

    identification_id, session_id = await _start_verified(client, verification_factory)
    first = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert first.status_code == 200

    # The challenge is gone; a replay cannot succeed (or fabricate state).
    replay = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert replay.status_code == 410
    assert _error(replay.json())["code"] == "verification_challenge_expired"


async def test_unprovisioned_bill_never_bypasses_verification(
    client, app, fake_clock, verification_factory
) -> None:
    """A bill without a configured code fails closed on any submitted code."""

    verification_factory(codes={})
    session_id = await create_consented_session(client)
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )
    identification_id = response.json()["identification_id"]

    answer = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "WHATEVER"},
    )

    assert answer.status_code == 401
    assert _error(answer.json())["code"] == "access_code_invalid"


async def test_access_via_unrelated_session_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    """Knowing the identification id must not be enough to verify anything."""

    identification_id, _own = await _start_verified(client, verification_factory)
    stranger = await create_consented_session(client)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": stranger, "access_code": "DEMO1234"},
    )

    assert response.status_code == 404
    assert _error(response.json())["code"] == "identification_not_found"


async def test_verification_rejected_when_consent_has_been_withdrawn(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    withdrawn = await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")
    assert withdrawn.status_code == 200

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert response.status_code == 403
    assert _error(response.json())["code"] == "consent_required"


async def test_expired_session_cannot_verify(
    client, app, fake_clock, verification_factory, monkeypatch
) -> None:
    """Session expiry is enforced independently of the challenge clock."""

    identification_id, session_id = await _start_verified(client, verification_factory)
    monkeypatch.setattr(
        "app.services.session_store._utcnow",
        lambda: datetime.now(UTC) + timedelta(minutes=61),
    )

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert response.status_code == 404
    assert _error(response.json())["code"] == "session_expired"


# --- Concurrent attempts -------------------------------------------------------


async def test_concurrent_failed_attempts_cannot_exceed_the_limit(
    client, verification_factory
) -> None:
    """Racing duplicate requests cannot defeat the server-side counter."""

    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    session_id = await create_consented_session(client)
    response = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
    )
    identification_id = response.json()["identification_id"]

    wrong = {"session_id": session_id, "access_code": "WRONGCODE"}
    responses = await asyncio.gather(
        *[
            client.post(f"/api/v1/identifications/{identification_id}/verify", json=wrong)
            for _ in range(6)
        ]
    )
    statuses = [r.status_code for r in responses]

    assert statuses.count(401) == 2, statuses
    assert statuses.count(403) == 4, statuses

    correct_after_lock = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert correct_after_lock.status_code == 403


# --- Protected financial information -------------------------------------------


async def test_protected_bill_requires_verification_by_this_session(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    unprotected = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )
    assert unprotected.status_code == 403
    assert _error(unprotected.json())["code"] == "verification_required"

    stranger = await create_consented_session(client)
    wrong_owner = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": stranger}
    )
    assert wrong_owner.status_code == 403  # same minimal answer, no record details
    assert _error(wrong_owner.json())["code"] == "verification_required"


async def test_missing_session_header_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, _session_id = await _start_verified(client, verification_factory)

    response = await client.get(f"/api/v1/verified-bills/{identification_id}")

    assert response.status_code == 422
    assert _error(response.json())["code"] == "validation_error"


async def test_expired_session_cannot_access_protected_bill(
    client, app, fake_clock, verification_factory, monkeypatch
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    monkeypatch.setattr(
        "app.services.session_store._utcnow",
        lambda: datetime.now(UTC) + timedelta(minutes=61),
    )
    response = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )

    assert response.status_code == 404
    assert _error(response.json())["code"] == "session_expired"


async def test_verified_bill_returns_recorded_amounts_from_the_fictional_record(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    response = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["identification_id"] == identification_id
    assert body["hospital_name"] == "Sunrise Multispeciality Hospital"
    assert body["bill_number"] == "SUN-2026-004512"
    assert body["amounts"]["total_amount"]["value"] == "12480.00"
    assert body["amounts"]["patient_payable"]["value"] == "6240.00"
    assert body["amounts"]["total_amount"]["authoritative"] is True
    assert body["comparison"]["status"] == "no_uploaded_image"  # manual entry: nothing to compare
    assert "itemized_charges" not in body  # never invented from absent fields
    assert "due_date" not in body
    assert body["uploaded_amounts"] is None


async def test_verified_bill_records_verification_state_in_memory(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "WRONGCODE"},
    )
    assert (
        await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": "DEMO1234"},
        )
    ).status_code == 200

    session = app.state.session_store._sessions.get(session_id)
    record = session.verifications[identification_id]
    assert record.verified_at >= fake_clock() - timedelta(minutes=1)
    assert record.failed_attempts_before_success == 1


# --- Privacy: no financial values, no access codes anywhere they must not be ----


async def test_failed_verification_reveals_no_financial_values(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "WRONGCODE"},
    )

    assert response.status_code == 401
    text = response.text
    assert "12480" not in text and "6240" not in text  # recorded amounts
    assert "SUN-2026-004512" not in text  # not even confirmed to the unverified caller


async def test_locked_verification_reveals_no_financial_values(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    for wrong_code in ("WRONG-A", "WRONG-B", "WRONG-C"):
        await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": wrong_code},
        )

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "WRONG-D"},
    )

    assert response.status_code == 403
    assert "6240" not in response.text and "12480" not in response.text


async def test_expired_challenge_reveals_no_financial_values(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)
    fake_clock.advance(minutes=6)

    response = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )

    assert response.status_code == 410
    assert "6240" not in response.text and "12480" not in response.text


async def test_unauthorized_protected_access_reveals_no_financial_values(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    not_verified = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )
    stranger = await create_consented_session(client)
    wrong_owner = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": stranger}
    )
    for caller_response in (not_verified, wrong_owner):
        assert caller_response.status_code == 403
        assert "12480" not in caller_response.text
        assert "6240" not in caller_response.text


async def test_access_codes_never_appear_in_responses_or_logs(
    client, app, fake_clock, verification_factory, caplog
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    with caplog.at_level(logging.INFO):
        first = await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": "SUPERSECRET-123"},
        )
        assert first.status_code == 401
        second = await client.post(
            f"/api/v1/identifications/{identification_id}/verify",
            json={"session_id": session_id, "access_code": "DEMO1234"},
        )
        assert second.status_code == 200
        check = await client.get(
            f"/api/v1/verified-bills/{identification_id}",
            headers={"X-Session-ID": session_id},
        )
        assert check.status_code == 200

    assert "SUPERSECRET-123" not in first.text
    assert "SUPERSECRET-123" not in check.text
    assert "SUPERSECRET-123" not in caplog.text
    assert "DEMO1234" not in caplog.text


async def test_identification_and_session_responses_remain_free_of_financial_fields(
    client, app, fake_clock, verification_factory
) -> None:
    identification_id, session_id = await _start_verified(client, verification_factory)

    session = app.state.session_store._sessions.get(session_id)
    record = next(i for i in session.identifications if i.identification_id == identification_id)
    assert record.extracted == {}  # manual entry carries no OCR amounts

    identification_text = (
        await client.post(
            "/api/v1/identifications",
            json={"session_id": session_id, "bill_number": "SUN-2026-004512"},
        )
    ).text
    assert "12480" not in identification_text and "6240" not in identification_text


async def test_ocr_values_cannot_overwrite_the_fictional_record(
    client, app, fake_clock, verification_factory
) -> None:
    """A manipulated demo upload must not change what the protected endpoint reports."""

    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    session_id = await create_consented_session(client)
    app.state.ocr_adapter = FakeOcrAdapter(
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Total Amount: Rs. 13,000.00 Amount Payable: Rs. 6,500.00"
    )

    upload = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert upload.status_code == 200, upload.json()
    identification_id = upload.json()["identification_id"]

    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["comparison"]["status"] == "amounts_differ"

    protected = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )
    assert protected.status_code == 200, protected.text
    body = protected.json()

    assert body["amounts"]["total_amount"]["value"] == "12480.00"  # record untouched
    assert body["amounts"]["patient_payable"]["value"] == "6240.00"
    assert body["uploaded_amounts"] == [
        {"label": "total", "value": "13000.00", "authoritative": False},
        {"label": "patient_payable", "value": "6500.00", "authoritative": False},
    ]
    assert "differ" in body["comparison"]["message"].lower()


async def test_matching_labelled_upload_reports_matched_comparison(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    session_id = await create_consented_session(client)
    app.state.ocr_adapter = FakeOcrAdapter(
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Total Amount: Rs. 12,480.00 Amount Payable: Rs. 6,240.00"
    )

    upload = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    identification_id = upload.json()["identification_id"]

    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert verified.status_code == 200
    assert verified.json()["comparison"]["status"] == "matched"

    protected = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )
    assert protected.json()["comparison"]["status"] == "matched"
    assert protected.json()["uploaded_amounts"] == [
        {"label": "total", "value": "12480.00", "authoritative": False},
        {"label": "patient_payable", "value": "6240.00", "authoritative": False},
    ]


async def test_insufficient_evidence_upload_verifies_but_reports_no_comparison(
    client, app, fake_clock, verification_factory
) -> None:
    """A valid code with unreliable uploaded amounts still verifies."""

    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    session_id = await create_consented_session(client)
    app.state.ocr_adapter = FakeOcrAdapter(
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 (totals unreadable)"
    )

    upload = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    identification_id = upload.json()["identification_id"]

    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": "DEMO1234"},
    )
    assert verified.status_code == 200
    assert verified.json()["comparison"]["status"] == "insufficient_evidence"

    protected = await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )
    body = protected.json()
    assert body["comparison"]["status"] == "insufficient_evidence"
    assert body["uploaded_amounts"] == []
