"""Phase 8 tests: local GenAI bill-explanation feature.

All tests mock the Ollama HTTP call — none requires a downloaded model or a
running Ollama server. Two mocking levels are used deliberately:

- HTTP level (:class:`httpx.MockTransport`): drives the real request/response
  handling of the Ollama client, including malformed bodies and timeouts.
- Client level (a fake ``generate``): exercises the explanation service and
  the API route without transport noise.

Authorization, consent and verification always run through the real existing
mechanisms — nothing is weakened or bypassed for the GenAI feature.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.explanations import (
    ExplanationFacts,
    ExplanationService,
    build_user_prompt,
    fallback_explanation,
    validator_problems,
)
from app.services.ollama_client import (
    OllamaChatClient,
    OllamaConnectionError,
    OllamaEmptyResponseError,
    OllamaMalformedResponseError,
    OllamaOutputTooLongError,
)
from tests.conftest import create_consented_session

SUNRISE_CODE = "DEMO1234"
SUNRISE_BILL = "SUN-2026-004512"

_SEED_FACTS = ExplanationFacts(
    bill_number=SUNRISE_BILL,
    hospital_name="Sunrise Multispeciality Hospital",
    bill_date="2026-03-14",
    total_minor_units=1_248_000,  # Rs 12480.00
    patient_payable_minor_units=624_000,  # Rs 6240.00
    comparison_status="no_uploaded_image",
    comparison_message="No bill image was uploaded, so there is nothing to compare.",
)

GOOD_EN = (
    "Your verified bill from Sunrise Multispeciality Hospital is dated "
    "2026-03-14. The recorded total is Rs 12480.00 and the patient-payable "
    "amount on record is Rs 6240.00. Please compare these values with the "
    "printed bill before paying."
)
GOOD_HI = "आपका बिल सत्यापित हो गया है। कृपया मूल बिल से राशियाँ मिलान करें।"
GOOD_KN = "ನಿಮ್ಮ ಬಿಲ್ ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದೆ. ಮೂಲ ಬಿಲ್‌ನೊಂದಿಗೆ ಮೊತ್ತಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."


# --- Helpers -------------------------------------------------------------------


def ollama_client_with(body: bytes, status: int = 200) -> OllamaChatClient:
    """An OllamaChatClient answering over a mock transport (real HTTP layer)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, request=request)

    return OllamaChatClient(
        base_url="http://localhost:11434",
        model="qwen3:1.7b",
        timeout_seconds=10.0,
        max_output_chars=2000,
        transport=httpx.MockTransport(handler),
    )


def failing_client(exc: Exception) -> Callable[[], OllamaChatClient]:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    def build() -> OllamaChatClient:
        return OllamaChatClient(
            base_url="http://localhost:11434",
            model="qwen3:1.7b",
            timeout_seconds=10.0,
            max_output_chars=2000,
            transport=httpx.MockTransport(handler),
        )

    return build


def mock_ollama_for(app, generated: str | Exception | None) -> None:
    """Replace the app's explanation service with a canned one."""

    if isinstance(generated, Exception):
        client = failing_client(generated)()
    else:
        client = ollama_client_with(
            json.dumps({"message": {"content": generated or ""}}).encode()
        )
    app.state.explanation_service = ExplanationService(client)


async def verify_sunrise_bill(client, session_id: str) -> str:
    """Identify and verify the Sunrise bill through the real API flow."""

    ident = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    assert ident.status_code == 200, ident.text
    identification_id = ident.json()["identification_id"]
    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": SUNRISE_CODE},
    )
    assert verified.status_code == 200, verified.text
    return identification_id


async def post_explanation(
    client, identification_id: str, session_id: str, **body
) -> httpx.Response:
    """POST the explanation request (header carries the session id)."""

    payload = {"language": "en", "ai_consent": True, **body}
    return await client.post(
        f"/api/v1/verified-bills/{identification_id}/explanation",
        json=payload,
        headers={"X-Session-ID": session_id},
    )


# --- Configuration --------------------------------------------------------------


def test_ollama_defaults_are_local() -> None:
    settings = Settings(_env_file=None, cors_origins="http://localhost:3000")

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen3:1.7b"
    assert settings.ollama_timeout_seconds == 60.0
    assert settings.ollama_max_output_chars == 2000


def test_ollama_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HBN_OLLAMA_BASE_URL", "http://127.0.0.1:11434/")
    monkeypatch.setenv("HBN_OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("HBN_OLLAMA_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("HBN_OLLAMA_MAX_OUTPUT_CHARS", "1500")

    settings = Settings(_env_file=None, cors_origins="http://localhost:3000")

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "qwen3:4b"
    assert settings.ollama_timeout_seconds == 30.0
    assert settings.ollama_max_output_chars == 1500


@pytest.mark.parametrize(
    "bad_url",
    ["", "ftp://localhost:11434", "localhost:11434", "http://host/?x=1"],
)
def test_invalid_ollama_base_url_is_rejected(bad_url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            cors_origins="http://localhost:3000",
            ollama_base_url=bad_url,
        )


def test_chat_payload_is_bounded_and_deterministic() -> None:
    client = ollama_client_with(b"{}")
    payload = client.build_chat_payload(system="S", user="U")

    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == pytest.approx(0.2)
    assert payload["options"]["num_predict"] <= 512
    assert payload["messages"][0]["role"] == "system"


# --- Ollama client over the real HTTP layer --------------------------------------


async def test_client_parses_a_wellformed_completion() -> None:
    body = json.dumps({"message": {"content": GOOD_EN}}).encode()
    text = await ollama_client_with(body).generate(system="S", user="U")
    assert text == GOOD_EN


async def test_unreachable_server_raises_connection_error() -> None:
    build = failing_client(httpx.ConnectError("refused"))
    with pytest.raises(OllamaConnectionError):
        await build().generate(system="S", user="U")


async def test_timeout_raises_connection_error() -> None:
    build = failing_client(httpx.ReadTimeout("slow"))
    with pytest.raises(OllamaConnectionError):
        await build().generate(system="S", user="U")


async def test_5xx_behaves_like_unavailable() -> None:
    with pytest.raises(OllamaConnectionError):
        await ollama_client_with(b"boom", status=503).generate(system="S", user="U")


async def test_non_json_body_is_malformed() -> None:
    with pytest.raises(OllamaMalformedResponseError):
        await ollama_client_with(b"<html>not json</html>").generate(system="S", user="U")


async def test_missing_message_is_malformed() -> None:
    with pytest.raises(OllamaMalformedResponseError):
        await ollama_client_with(b'{"done": true}').generate(system="S", user="U")


async def test_empty_content_is_rejected() -> None:
    with pytest.raises(OllamaEmptyResponseError):
        await ollama_client_with(b'{"message": {"content": "  "}}').generate(
            system="S", user="U"
        )


async def test_excessive_output_is_discarded_not_truncated() -> None:
    long_text = "x" * 2001
    with pytest.raises(OllamaOutputTooLongError):
        await ollama_client_with(
            json.dumps({"message": {"content": long_text}}).encode()
        ).generate(system="S", user="U")


# --- Output validation -----------------------------------------------------------


@pytest.mark.parametrize("text", [GOOD_EN, GOOD_HI, GOOD_KN])
def test_validator_accepts_facts_only_prose(text: str) -> None:
    assert validator_problems(text, _SEED_FACTS) == []


def test_validator_rejects_invented_amounts() -> None:
    problems = validator_problems(
        "The payable amount is Rs 999.00, please pay promptly.", _SEED_FACTS
    )
    assert any(p.startswith("unsupported_amount") for p in problems)


def test_validator_rejects_invented_dates() -> None:
    problems = validator_problems("Due on 2026-04-01.", _SEED_FACTS)
    assert any(p.startswith("unsupported_date") for p in problems)


def test_validator_rejects_forbidden_claims() -> None:  # fraud/payment/coverage
    for text in (
        "This looks like fraud.",
        "The bill has been paid.",
        "Your insurance has approved the claim.",
        "Payment deadline is next week.",
    ):
        assert validator_problems(text, _SEED_FACTS), text


def test_validator_accepts_the_authoritative_amounts() -> None:
    assert validator_problems("Total Rs 12,480.00 and payable Rs 6240.", _SEED_FACTS) == []


# --- Explanation service and fallbacks -------------------------------------------


async def test_service_returns_validated_generated_text() -> None:
    outcome = await ExplanationService(ollama_client_with(
        json.dumps({"message": {"content": GOOD_EN}}).encode()
    )).explain(_SEED_FACTS, "en")

    assert outcome.source == "generated"
    assert outcome.text == GOOD_EN
    assert outcome.reason is None


@pytest.mark.parametrize(
    "client_factory",
    [
        lambda: failing_client(httpx.ConnectError("down"))(),
        lambda: ollama_client_with(b"not json"),
        lambda: ollama_client_with(b'{"message": {"content": ""}}'),
        lambda: ollama_client_with(
            json.dumps({"message": {"content": "y" * 3000}}).encode()
        ),
    ],
)
async def test_every_model_failure_produces_the_fallback(client_factory) -> None:
    first = await ExplanationService(client_factory()).explain(_SEED_FACTS, "en")
    assert first.source == "fallback"
    assert "12480.00" in first.text
    assert "6240.00" in first.text


async def test_unsafe_generated_text_is_discarded_for_fallback() -> None:
    unsafe = "The payable amount is Rs 999.00 and the bill has been paid."
    outcome = await ExplanationService(ollama_client_with(
        json.dumps({"message": {"content": unsafe}}).encode()
    )).explain(_SEED_FACTS, "en")

    assert outcome.source == "fallback"
    assert outcome.text != unsafe
    assert outcome.reason is not None  # the exact first problem may vary in order


async def test_fallback_is_deterministic() -> None:
    service = ExplanationService(ollama_client_with(b'{"message": {"content": ""}}'))
    first = await service.explain(_SEED_FACTS, "en")
    second = await service.explain(_SEED_FACTS, "en")
    assert first.text == second.text


@pytest.mark.parametrize("code", ["en", "hi", "kn"])
async def test_fallback_covers_every_language(code: str) -> None:
    outcome = await ExplanationService(ollama_client_with(b"{}")).explain(
        _SEED_FACTS, code
    )
    assert outcome.source == "fallback"
    assert SUNRISE_BILL in outcome.text
    assert outcome.text == fallback_explanation(_SEED_FACTS, code)


def test_prompt_contains_no_patient_or_secret_data() -> None:
    prompt = build_user_prompt(_SEED_FACTS, "en")
    lowered = prompt.lower()
    assert "access code" not in lowered
    assert "session" not in lowered
    assert SUNRISE_CODE.lower() not in lowered
    assert "12480.00" in prompt and "6240.00" in prompt


def test_fallback_never_claims_payment_or_coverage() -> None:
    for code in ("en", "hi", "kn"):
        text = fallback_explanation(_SEED_FACTS, code).lower()
        for phrase in ("has been paid", "insurance", "fraud", "overcharg"):
            assert phrase not in text


# --- API endpoint (real session/consent/verification flow) ------------------------


async def test_explanation_in_english_generated(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    response = await post_explanation(client, identification_id, session_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "generated"
    assert body["language"] == "en"
    assert body["explanation"] == GOOD_EN
    assert body["fallback_reason"] is None
    facts = body["facts"]
    assert facts["bill_number"] == SUNRISE_BILL
    assert facts["amounts"]["total"]["value"] == "12480.00"
    assert facts["amounts"]["total"]["authoritative"] is True
    assert facts["amounts"]["patient_payable"]["value"] == "6240.00"
    # Generated prose is always flagged as non-authoritative by its source,
    # while every trusted amount carries authoritative=True in facts.
    assert body["source"] in {"generated", "fallback"}
    assert all(
        amount["authoritative"] is True for amount in facts["amounts"].values()
    )


async def test_explanation_in_hindi_and_kannada(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    for language, content in (("hi", GOOD_HI), ("kn", GOOD_KN)):
        mock_ollama_for(app, content)
        response = await post_explanation(client, identification_id, session_id, language=language)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source"] == "generated"
        assert body["language"] == language
        assert body["explanation"] == content


@pytest.mark.parametrize("language", ["de", "fr", "mr", "", None])
async def test_unsupported_languages_are_rejected(
    client, app, fake_clock, verification_factory, language
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    response = await client.post(
        f"/api/v1/verified-bills/{identification_id}/explanation",
        json={} if language is None else {"language": language, "ai_consent": True},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("consent_value", [False, None, "yes"])
async def test_missing_or_false_ai_consent_is_rejected(
    client, app, fake_clock, verification_factory, consent_value
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    body = {"language": "en"}
    if consent_value is not None:
        body["ai_consent"] = consent_value

    response = await client.post(
        f"/api/v1/verified-bills/{identification_id}/explanation",
        json=body,
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 422, response.text
    assert "ai_consent" in json.dumps(response.json())


async def test_unverified_bill_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    ident = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": SUNRISE_BILL},
    )
    identification_id = ident.json()["identification_id"]

    response = await post_explanation(client, identification_id, session_id)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "verification_required"


async def test_nonexistent_identification_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)

    response = await post_explanation(client, "0f2a6cc4d4b74d02a25a5c9e40f65c31", session_id)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "verification_required"


async def test_unknown_session_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    stranger_id = "a" * 32
    response = await post_explanation(client, identification_id, stranger_id)
    assert response.status_code == 404, response.text  # session privacy


async def test_another_sessions_verified_bill_is_rejected(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    other_id = await create_consented_session(client)  # different live session
    response = await post_explanation(client, identification_id, other_id)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "verification_required"


@pytest.mark.parametrize("mode", ["missing", "withdrawn"])
async def test_consent_is_enforced_before_generation(
    client, app, fake_clock, verification_factory, mode
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    if mode == "withdrawn":
        withdraw = await client.post(
            f"/api/v1/sessions/{session_id}/consent/withdraw", json={}
        )
        assert withdraw.status_code == 200, withdraw.text
    else:  # a fresh session without consent
        fresh = await client.post("/api/v1/sessions")
        session_id = fresh.json()["session_id"]

    response = await post_explanation(client, identification_id, session_id)
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "consent_required"
    assert "explanation" not in json.dumps(response.json())


async def test_withdrawn_consent_never_yields_an_explanation(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)
    await client.post(f"/api/v1/sessions/{session_id}/consent/withdraw", json={})

    response = await post_explanation(client, identification_id, session_id)
    assert response.status_code == 403, response.text
    assert "explanation" not in json.dumps(response.json())


async def test_client_supplied_financial_values_are_ignored(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, GOOD_EN)
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    response = await client.post(
        f"/api/v1/verified-bills/{identification_id}/explanation",
        json={
            "language": "en",
            "ai_consent": True,
            "amounts": {"total": {"value": "99.00", "authoritative": True}},
            "total": "99.00",
            "patient_payable": "99.00",
            "bill_date": "2000-01-01",
            "bill_number": "FAKE-000",
            "comparison": {"status": "matched", "message": "client says match"},
            "paid": True,
        },
        headers={"X-Session-ID": session_id},
    )

    assert response.status_code == 200, response.text
    facts = response.json()["facts"]
    assert facts["amounts"]["total"]["value"] == "12480.00"
    assert facts["amounts"]["patient_payable"]["value"] == "6240.00"
    assert facts["bill_date"] == "2026-03-14"
    assert facts["bill_number"] == SUNRISE_BILL
    assert facts["comparison"]["status"] == "no_uploaded_image"


async def test_model_down_falls_back_over_the_api(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, httpx.ConnectError("down"))
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    response = await post_explanation(client, identification_id, session_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] == "ollama_unreachable"
    assert "12480.00" in body["explanation"]


async def test_contradicting_generated_amounts_fall_back_over_the_api(
    client, app, fake_clock, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, "You must pay Rs 999.00 total.")
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    response = await post_explanation(client, identification_id, session_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fallback"
    assert body["fallback_reason"] is not None
    assert "999.00" not in body["explanation"]


async def test_no_leakage_through_logs_or_responses(
    client, app, fake_clock, verification_factory, caplog
) -> None:
    verification_factory(codes={"bill-sun-004512": SUNRISE_CODE})
    mock_ollama_for(app, httpx.ConnectError("down"))
    session_id = await create_consented_session(client)
    identification_id = await verify_sunrise_bill(client, session_id)

    with caplog.at_level(logging.DEBUG):
        response = await post_explanation(client, identification_id, session_id)

    assert response.status_code == 200
    rendered = json.dumps(response.json())
    assert SUNRISE_CODE not in rendered  # access code never appears
    assert "Traceback" not in rendered
    assert "C:\\" not in rendered
    for record in caplog.records:
        message = record.getMessage()
        assert SUNRISE_CODE not in message
        assert session_id not in message
        assert "Explain this bill summary" not in message  # prompts never logged


async def test_existing_behaviour_unchanged(client, app) -> None:
    """The Phase 8 router must not disturb the existing route contract."""

    health = await client.get("/api/v1/health")
    assert health.status_code == 200

    spec = (await client.get("/openapi.json")).json()
    paths = set(spec["paths"])
    assert {
        "/api/v1/sessions",
        "/api/v1/identifications",
        "/api/v1/identifications/{identification_id}/verify",
        "/api/v1/verified-bills/{identification_id}",
        "/api/v1/help-requests",
        "/api/v1/staff/help-requests",
    } <= paths
    assert "/api/v1/verified-bills/{identification_id}/explanation" in paths
