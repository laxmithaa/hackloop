"""Phase 9 Part B tests: personalised explanations and the approved glossary.

All model calls are mocked; authorization and verification use the real flow.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from httpx import AsyncClient

from app.services.bill_facts import ExplanationFacts
from app.services.bill_glossary import GLOSSARY_TERM_CODES, GLOSSARY_TERMS
from app.services.personalization import (
    PersonalizationService,
    base_explanation,
    short_fallback,
    simple_fallback,
)
from tests.ai_support import (
    SUNRISE_BILL,
    SUNRISE_CODE,
    install_personalization_service,
    ollama_answer,
    post_personalized,
    unreachable_client,
    verified_bill,
)
from tests.conftest import create_consented_session

SEED_FACTS = ExplanationFacts(
    bill_number=SUNRISE_BILL,
    hospital_name="Sunrise Multispeciality Hospital",
    bill_date="2026-03-14",
    total_minor_units=1_248_000,  # Rs 12480.00
    patient_payable_minor_units=624_000,  # Rs 6240.00
    comparison_status="no_uploaded_image",
    comparison_message="No bill image was uploaded, so there is nothing to compare.",
)

SIMPLE_OK = (
    "Your bill from Sunrise Multispeciality Hospital is dated 2026-03-14. "
    "The total is Rs 12480.00 and your share is Rs 6240.00."
)
SHORT_OK = "Sunrise Multispeciality Hospital, 2026-03-14: total Rs 12480.00, share Rs 6240.00."
SIMPLE_HI = "आपका बिल सत्यापित है। कुल राशि Rs 12480.00 है और आपका हिस्सा Rs 6240.00 है।"
SIMPLE_KN = "ನಿಮ್ಮ ಬಿಲ್ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದೆ. ಒಟ್ಟು Rs 12480.00 ಮತ್ತು ನಿಮ್ಮ ಪಾಲು Rs 6240.00."


@pytest.fixture(autouse=True)
def _provision_demo_access_code(app, verification_factory) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})


# --- Glossary ----------------------------------------------------------------------


def test_every_term_is_defined_in_every_supported_language() -> None:
    assert len(GLOSSARY_TERM_CODES) == 8
    for code in GLOSSARY_TERM_CODES:
        entry = GLOSSARY_TERMS[code]
        assert set(entry.definitions) == {"en", "hi", "kn"}
        for language, text in entry.definitions.items():
            assert len(text.strip()) > 40, (code, language)
            # Definitions are about meaning, never about this bill's figures.
            assert "Rs " not in text, (code, language)


def test_unavailable_terms_say_the_record_does_not_include_them() -> None:
    for code in (
        "insurance_covered_amount",
        "amount_already_paid",
        "outstanding_balance",
        "co_payment",
    ):
        entry = GLOSSARY_TERMS[code]
        assert entry.available_in_record is False
        assert "does not include" in entry.definitions["en"], code


async def test_term_mode_returns_the_approved_definition_without_the_model() -> None:
    service = PersonalizationService(ollama_answer("SHOULD NOT BE USED"))

    outcome = await service.personalize(
        SEED_FACTS, mode="term", language="en", term="outstanding_balance"
    )

    assert outcome.source == "glossary"
    assert outcome.text.startswith("The outstanding balance is")
    assert "SHOULD NOT BE USED" not in outcome.text


async def test_term_mode_adds_a_grounded_sentence_for_available_figures() -> None:
    service = PersonalizationService(unreachable_client())

    outcome = await service.personalize(
        SEED_FACTS, mode="term", language="en", term="total_bill_amount"
    )

    assert outcome.source == "glossary"
    assert "Rs 12480.00" in outcome.text


@pytest.mark.parametrize("language", ["hi", "kn"])
async def test_term_definitions_are_available_in_each_language(language: str) -> None:
    service = PersonalizationService(unreachable_client())

    outcome = await service.personalize(
        SEED_FACTS, mode="term", language=language, term="bill_verification"
    )

    assert outcome.source == "glossary"
    # The approved definition is used verbatim; available terms additionally
    # get one grounded sentence about this bill.
    assert GLOSSARY_TERMS["bill_verification"].definitions[language] in outcome.text


# --- Simple / short modes -----------------------------------------------------------


async def test_simple_mode_accepts_a_valid_rewrite() -> None:
    service = PersonalizationService(ollama_answer(SIMPLE_OK))

    outcome = await service.personalize(SEED_FACTS, mode="simple", language="en")

    assert outcome.source == "generated"
    assert outcome.text == SIMPLE_OK


async def test_simple_mode_rejects_an_invented_amount() -> None:
    service = PersonalizationService(ollama_answer("Your share is only Rs 500.00, so pay that."))

    outcome = await service.personalize(SEED_FACTS, mode="simple", language="en")

    assert outcome.source == "fallback"
    assert outcome.reason == "unsupported_amount:500.00"
    assert outcome.text == simple_fallback(SEED_FACTS, "en")
    assert "500" not in outcome.text
    assert "Rs 12480.00" in outcome.text
    assert "Rs 6240.00" in outcome.text


async def test_short_mode_rejects_an_unrecorded_date() -> None:
    service = PersonalizationService(ollama_answer("Bill from 2026-04-01, total 12480.00."))

    outcome = await service.personalize(SEED_FACTS, mode="short", language="en")

    assert outcome.source == "fallback"
    assert outcome.reason == "unsupported_date:2026-04-01"
    assert outcome.text == short_fallback(SEED_FACTS, "en")


async def test_short_mode_rejects_a_correctness_claim() -> None:
    service = PersonalizationService(ollama_answer("The bill was overcharged, so do not pay."))

    outcome = await service.personalize(SEED_FACTS, mode="short", language="en")

    assert outcome.source == "fallback"
    assert outcome.reason.startswith("forbidden_claim:")


@pytest.mark.parametrize(
    ("language", "answer"),
    [("hi", SIMPLE_HI), ("kn", SIMPLE_KN)],
)
async def test_localised_rewrites_are_accepted(language: str, answer: str) -> None:
    service = PersonalizationService(ollama_answer(answer))

    outcome = await service.personalize(SEED_FACTS, mode="simple", language=language)

    assert outcome.source == "generated"


async def test_language_script_mismatch_falls_back_to_the_requested_language() -> None:
    service = PersonalizationService(ollama_answer(SIMPLE_OK))

    outcome = await service.personalize(SEED_FACTS, mode="simple", language="hi")

    assert outcome.source == "fallback"
    assert outcome.reason == "language_mismatch:hi"
    assert outcome.text == simple_fallback(SEED_FACTS, "hi")
    assert "कुल राशि" in outcome.text


@pytest.mark.parametrize("mode", ["simple", "short"])
async def test_model_outage_falls_back_to_localised_text(mode: str) -> None:
    service = PersonalizationService(unreachable_client())

    outcome = await service.personalize(SEED_FACTS, mode=mode, language="en")

    assert outcome.source == "fallback"
    assert outcome.reason == "ollama_unreachable"
    assert "Rs 12480.00" in outcome.text


async def test_empty_completion_falls_back() -> None:
    service = PersonalizationService(ollama_answer("   "))

    outcome = await service.personalize(SEED_FACTS, mode="simple", language="en")

    assert outcome.source == "fallback"
    assert outcome.reason == "ollama_empty_content"


async def test_oversized_rewrite_is_rejected() -> None:
    long_text = SIMPLE_OK + " " + ("This sentence adds length. " * 12)
    service = PersonalizationService(ollama_answer(long_text), max_chars=300)

    outcome = await service.personalize(SEED_FACTS, mode="simple", language="en")

    assert outcome.source == "fallback"
    assert outcome.reason.startswith("output_too_long:")


@pytest.mark.parametrize("language", ["en", "hi", "kn"])
def test_fallbacks_preserve_every_recorded_fact(language: str) -> None:
    simple = simple_fallback(SEED_FACTS, language)
    short = short_fallback(SEED_FACTS, language)

    for text in (simple, short):
        assert "Rs 12480.00" in text
        assert "Rs 6240.00" in text
        assert SEED_FACTS.bill_number in text
    assert SEED_FACTS.hospital_name in simple
    assert SEED_FACTS.bill_date in simple
    assert SEED_FACTS.bill_date in short


def test_fallbacks_keep_total_and_payable_distinct() -> None:
    text = simple_fallback(SEED_FACTS, "en")

    assert text.count("Rs 12480.00") >= 1
    assert text.count("Rs 6240.00") >= 1
    assert "total" in text.lower()


@pytest.mark.parametrize(
    ("status", "expected"),
    [("matched", "match"), ("amounts_differ", "differ")],
)
def test_simplification_preserves_the_comparison_outcome(status: str, expected: str) -> None:
    facts = replace(SEED_FACTS, comparison_status=status, comparison_message="note")

    assert expected in simple_fallback(facts, "en")
    assert expected in base_explanation(facts, "en")


def test_insurance_term_never_invents_a_figure() -> None:
    text = GLOSSARY_TERMS["insurance_covered_amount"].definitions["en"]

    assert "Rs " not in text
    assert "does not include insurance information" in text


# --- Endpoint ---------------------------------------------------------------------


async def test_endpoint_returns_a_personalised_explanation(client: AsyncClient, app) -> None:
    session_id, identification_id = await verified_bill(client)
    install_personalization_service(app, SIMPLE_OK)

    response = await post_personalized(client, identification_id, session_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "generated"
    assert body["mode"] == "simple"
    assert body["term"] is None
    assert body["explanation"] == SIMPLE_OK
    assert body["facts"]["bill_number"] == SUNRISE_BILL
    assert response.headers["cache-control"] == "no-store"


async def test_endpoint_term_mode_uses_the_glossary(client: AsyncClient, app) -> None:
    session_id, identification_id = await verified_bill(client)
    install_personalization_service(app, "SHOULD NOT BE USED")

    response = await post_personalized(
        client,
        identification_id,
        session_id,
        mode="term",
        term="insurance_covered_amount",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "glossary"
    assert body["term"] == "insurance_covered_amount"
    assert "insurance" in body["explanation"].lower()
    assert "Rs " not in body["explanation"]
    assert "SHOULD NOT BE USED" not in body["explanation"]


async def test_endpoint_falls_back_when_the_model_is_down(client: AsyncClient, app) -> None:
    session_id, identification_id = await verified_bill(client)
    install_personalization_service(app, unreachable_client())

    response = await post_personalized(client, identification_id, session_id, mode="short")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] == "ollama_unreachable"
    assert "Rs 12480.00" in body["explanation"]


async def test_term_mode_requires_a_term(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await post_personalized(client, identification_id, session_id, mode="term")

    assert response.status_code == 422


async def test_term_is_rejected_for_other_modes(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await post_personalized(
        client, identification_id, session_id, mode="simple", term="total_bill_amount"
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"mode": "verbose"},
        {"language": "fr"},
        {"mode": "term", "term": "not_a_term"},
    ],
)
async def test_unsupported_options_are_rejected(client: AsyncClient, body: dict) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await post_personalized(client, identification_id, session_id, **body)

    assert response.status_code == 422


async def test_financial_overrides_are_rejected(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await post_personalized(client, identification_id, session_id, total="9999.00")

    assert response.status_code == 422


async def test_missing_ai_consent_is_rejected(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)

    response = await client.post(
        f"/api/v1/verified-bills/{identification_id}/personalized-explanation",
        json={"mode": "simple", "language": "en"},
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 422


async def test_unauthorized_personalization_is_rejected(client: AsyncClient) -> None:
    session_id = await create_consented_session(client)
    identified = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    identification_id = identified.json()["identification_id"]

    response = await post_personalized(client, identification_id, session_id)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "verification_required"


async def test_cross_session_personalization_is_rejected(client: AsyncClient) -> None:
    _, identification_a = await verified_bill(client)
    session_b = await create_consented_session(client)

    response = await post_personalized(client, identification_a, session_b)

    assert response.status_code == 403


async def test_withdrawn_consent_blocks_personalization(client: AsyncClient) -> None:
    session_id, identification_id = await verified_bill(client)
    await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw")

    response = await post_personalized(client, identification_id, session_id)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "consent_required"


async def test_unknown_session_is_rejected(client: AsyncClient) -> None:
    _, identification_id = await verified_bill(client)

    response = await post_personalized(client, identification_id, "A" * 43)

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("language", "expected_fragment"),
    [("hi", "कुल राशि"), ("kn", "ಒಟ್ಟು")],
)
async def test_endpoint_fallbacks_are_localised(
    client: AsyncClient, app, language: str, expected_fragment: str
) -> None:
    session_id, identification_id = await verified_bill(client)
    install_personalization_service(app, unreachable_client())

    response = await post_personalized(client, identification_id, session_id, language=language)

    assert response.status_code == 200
    assert response.json()["language"] == language
    assert expected_fragment in response.json()["explanation"]
