"""Phase 9 Part C tests: caregiver shares and summaries.

Authorization is exercised for real: a patient session must verify the bill,
grant caregiver-sharing consent and hold a live share code. Every denial path
(unknown/expired/revoked code, withdrawn consent, expired session, cross-bill
use) is asserted. Model calls are mocked.
"""

from __future__ import annotations

import logging
from dataclasses import replace

import pytest
from httpx import AsyncClient

from app.schemas.caregiver import CAREGIVER_SHARED_FIELDS
from app.services.bill_facts import ExplanationFacts
from app.services.caregiver import (
    CaregiverShareStore,
    CaregiverSummaryService,
    caregiver_template,
)
from tests.ai_support import (
    SUNRISE_BILL,
    SUNRISE_CODE,
    create_share,
    get_summary,
    install_caregiver_service,
    install_share_store,
    ollama_answer,
    unreachable_client,
    verified_bill,
)
from tests.conftest import FakeClock, create_consented_session

SEED_FACTS = ExplanationFacts(
    bill_number=SUNRISE_BILL,
    hospital_name="Sunrise Multispeciality Hospital",
    bill_date="2026-03-14",
    total_minor_units=1_248_000,  # Rs 12480.00
    patient_payable_minor_units=624_000,  # Rs 6240.00
    comparison_status="no_uploaded_image",
    comparison_message="No bill image was uploaded, so there is nothing to compare.",
)

GOOD_SUMMARY = (
    "Sunrise Multispeciality Hospital bill SUN-2026-004512 dated 2026-03-14 has a "
    "recorded total of Rs 12480.00 and a patient share of Rs 6240.00. It passed "
    "access-code verification. Contact the hospital billing desk for clarification."
)


@pytest.fixture(autouse=True)
def _provision_demo_access_code(app, verification_factory) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})


@pytest.fixture
def deterministic_share_store(app, fake_clock: FakeClock):
    store = CaregiverShareStore(ttl_minutes=60, now_fn=fake_clock)
    install_share_store(app, store)
    return store


async def share_bill(client: AsyncClient, language: str = "en") -> tuple[str, str, str]:
    """Verified (session, identification) plus an authorised share code."""

    session_id, identification_id = await verified_bill(client)
    created = await create_share(client, identification_id, session_id, language=language)
    assert created.status_code == 201, created.text
    return session_id, identification_id, created.json()["share_code"]


# --- Share creation -----------------------------------------------------------------


async def test_share_creation_returns_a_one_time_code(client: AsyncClient) -> None:
    session_id, identification_id, code = await share_bill(client)

    response = await create_share(client, identification_id, session_id)

    assert response.status_code == 201
    body = response.json()
    assert body["identification_id"] == identification_id
    assert body["share_id"] != body["share_code"]
    assert len(body["share_code"]) >= 20
    assert body["shared_fields"] == list(CAREGIVER_SHARED_FIELDS)
    assert body["language"] == "en"
    assert body["expires_at"]
    assert response.headers["cache-control"] == "no-store"
    assert code


async def test_share_requires_explicit_sharing_consent(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await client.post(
        f"/api/v1/verified-bills/{identification_id}/caregiver-share",
        json={"language": "en"},
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 422


async def test_share_requires_a_verified_bill(client: AsyncClient) -> None:
    session_id = await create_consented_session(client)
    identified = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    identification_id = identified.json()["identification_id"]

    response = await create_share(client, identification_id, session_id)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "verification_required"


async def test_share_requires_granted_consent(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)
    await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")

    response = await create_share(client, identification_id, session_id)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "consent_required"


async def test_share_limits_are_enforced(client: AsyncClient) -> None:
    session_id, identification_id, _ = await share_bill(client)
    await create_share(client, identification_id, session_id)
    await create_share(client, identification_id, session_id)

    fourth = await create_share(client, identification_id, session_id)

    assert fourth.status_code == 409
    assert fourth.json()["error"]["code"] == "caregiver_share_limit_reached"


# --- Summary happy paths --------------------------------------------------------------


async def test_summary_uses_the_template_when_the_model_is_down(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, unreachable_client())

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] == "ollama_unreachable"
    assert body["verification_status"] == "verified"
    assert body["facts"]["bill_number"] == SUNRISE_BILL
    assert body["facts"]["uploaded_amounts"] is None
    assert "Recorded total bill amount: Rs 12480.00" in body["summary"]
    assert "Recorded amount payable by the patient: Rs 6240.00" in body["summary"]
    assert "clinical" not in body["summary"]
    assert response.headers["cache-control"] == "no-store"
    assert "session" not in response.text.lower()
    assert body["expires_at"]


async def test_summary_accepts_a_validated_rewrite(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, GOOD_SUMMARY)

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 200
    assert response.json()["source"] == "generated"
    assert response.json()["summary"] == GOOD_SUMMARY


# --- Summary rejection and fallback ----------------------------------------------------


async def test_summary_rejects_an_invented_amount(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, "The total is Rs 999.00. Contact the hospital billing desk.")

    response = await get_summary(client, identification_id, code)

    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] == "unsupported_amount:999.00"
    assert "999" not in body["summary"]
    assert "Rs 12480.00" in body["summary"]


async def test_summary_rejects_an_invented_date(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, "Bill dated 2026-04-01. Total Rs 12480.00.")

    response = await get_summary(client, identification_id, code)

    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] == "unsupported_date:2026-04-01"


async def test_summary_rejects_correctness_or_payment_claims(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, "The hospital overcharged you, so you owe Rs 12480.00 now.")

    response = await get_summary(client, identification_id, code)

    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"].startswith("forbidden_claim:")


# --- Languages --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "fragment"),
    [("hi", "जानने योग्य बातें"), ("kn", "ತಿಳಿಯಬೇಕಾದ ಅಂಶಗಳು")],
)
async def test_summary_languages(client: AsyncClient, app, language: str, fragment: str) -> None:
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, unreachable_client())

    response = await get_summary(client, identification_id, code, language=language)

    assert response.status_code == 200
    assert response.json()["language"] == language
    assert fragment in response.json()["summary"]


async def test_summary_defaults_to_the_share_language(client: AsyncClient, app) -> None:
    _, identification_id, code = await share_bill(client, language="kn")
    install_caregiver_service(app, unreachable_client())

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 200
    assert response.json()["language"] == "kn"
    assert "ಒಟ್ಟು ಬಿಲ್ ಮೊತ್ತ" in response.json()["summary"]


async def test_unsupported_language_is_rejected(client: AsyncClient) -> None:
    _, identification_id, code = await share_bill(client)

    response = await get_summary(client, identification_id, code, language="fr")

    assert response.status_code == 422


# --- Authorization failures ----------------------------------------------------------------


async def test_invalid_share_code_is_rejected(client: AsyncClient) -> None:
    _, identification_id, _ = await share_bill(client)

    response = await get_summary(client, identification_id, "Z" * 32)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "caregiver_share_invalid"


async def test_missing_share_code_is_rejected(client: AsyncClient) -> None:
    _, identification_id, _ = await share_bill(client)

    response = await client.get(f"/api/v1/verified-bills/{identification_id}/caregiver-summary")

    assert response.status_code == 422


async def test_share_code_is_scoped_to_one_bill(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)
    _, other_identification = await verified_bill(client)
    created = await create_share(client, identification_id, session_id)
    code = created.json()["share_code"]

    response = await get_summary(client, other_identification, code)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "caregiver_share_invalid"


async def test_revoked_share_stops_working(client: AsyncClient) -> None:
    session_id, identification_id, code = await share_bill(client)

    revoked = await client.delete(
        f"/api/v1/verified-bills/{identification_id}/caregiver-share",
        headers={"X-Session-ID": session_id},
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_shares"] == 1

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 403


async def test_revoking_with_no_shares_returns_zero(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await client.delete(
        f"/api/v1/verified-bills/{identification_id}/caregiver-share",
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200
    assert response.json()["revoked_shares"] == 0


async def test_withdrawing_consent_revokes_every_share(
    client: AsyncClient, app, deterministic_share_store
) -> None:
    session_id, identification_id, code = await share_bill(client)
    assert deterministic_share_store.active_count() == 1

    await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")

    assert deterministic_share_store.active_count() == 0
    response = await get_summary(client, identification_id, code)
    assert response.status_code == 403


async def test_expired_share_is_rejected(
    client: AsyncClient, deterministic_share_store, fake_clock: FakeClock
) -> None:
    _, identification_id, code = await share_bill(client)

    fake_clock.advance(minutes=61)

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "caregiver_share_invalid"


async def test_expired_patient_session_invalidates_the_summary(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, identification_id, code = await share_bill(client)

    from datetime import UTC, datetime, timedelta

    from app.services import session_store as session_store_module

    monkeypatch.setattr(
        session_store_module,
        "_utcnow",
        lambda: datetime.now(UTC) + timedelta(hours=120),
    )

    response = await get_summary(client, identification_id, code)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "caregiver_share_invalid"


async def test_cross_session_summary_is_rejected(client: AsyncClient) -> None:
    _, _identification_a, code_a = await share_bill(client)
    _, identification_b = await verified_bill(client)

    # The correct bill id but another patient's verification: still denied.
    response = await get_summary(client, identification_b, code_a)
    assert response.status_code == 403


# --- Template and privacy properties --------------------------------------------------------


@pytest.mark.parametrize("language", ["en", "hi", "kn"])
def test_template_restates_both_amounts(language: str) -> None:
    template = caregiver_template(SEED_FACTS, language)

    assert "Rs 12480.00" in template
    assert "Rs 6240.00" in template
    assert SEED_FACTS.bill_number in template
    assert SEED_FACTS.bill_date in template


def test_template_never_fabricates_missing_fields() -> None:
    facts = replace(
        SEED_FACTS,
        insurance_covered_minor_units=None,
        amount_paid_minor_units=None,
        outstanding_balance_minor_units=None,
    )

    template = caregiver_template(facts, "en")

    assert "insurance" not in template.lower()
    assert "None" not in template
    assert "outstanding" not in template.lower()


def test_template_gives_no_payment_or_correctness_advice() -> None:
    template = caregiver_template(SEED_FACTS, "en").lower()

    assert "should pay" not in template
    assert "pay now" not in template
    assert "fraud" not in template
    assert "correct" in template  # only the explicit disclaimer
    assert "verification does not mean the charges are correct" in template


async def test_share_codes_are_stored_hashed(
    client: AsyncClient, deterministic_share_store
) -> None:
    _, _, code = await share_bill(client)

    assert code not in repr(deterministic_share_store.__dict__)


async def test_caregiver_logs_do_not_include_the_summary_or_code(
    client: AsyncClient, app, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.services.caregiver")
    _, identification_id, code = await share_bill(client)
    install_caregiver_service(app, unreachable_client())

    await get_summary(client, identification_id, code)

    assert code not in caplog.text
    assert "Rs 12480.00" not in caplog.text


async def test_summary_service_is_shared_and_reuses_the_template() -> None:
    service = CaregiverSummaryService(unreachable_client())

    outcome = await service.summarize(SEED_FACTS, "en")

    assert outcome.source == "fallback"
    assert outcome.text == caregiver_template(SEED_FACTS, "en")


async def test_summary_service_accepts_valid_localised_text() -> None:
    kannada = (
        "ಸನ್‌ರೈಸ್ ಆಸ್ಪತ್ರೆಯ ಬಿಲ್ SUN-2026-004512, ದಿನಾಂಕ 2026-03-14. "
        "ಒಟ್ಟು Rs 12480.00, ರೋಗಿ ಪಾಲು Rs 6240.00. ಬಿಲ್ಲಿಂಗ್ ಡೆಸ್ಕ್ ಸಂಪರ್ಕಿಸಿ."
    )
    service = CaregiverSummaryService(ollama_answer(kannada))

    outcome = await service.summarize(SEED_FACTS, "kn")

    assert outcome.source == "generated"
    assert outcome.text == kannada


async def test_share_store_revokes_by_session() -> None:
    store = CaregiverShareStore(ttl_minutes=60)
    share, code = store.create(identification_id="ident-1", session_id="session-1", language="en")
    assert store.authorize("ident-1", code) == share

    assert store.revoke_session("session-1") == 1
    assert store.authorize("ident-1", code) is None
