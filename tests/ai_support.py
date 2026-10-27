"""Shared helpers for the Phase 9 GenAI tests.

Every model interaction is mocked at the HTTP transport level, so the normal
test suite never needs a downloaded model, a running Ollama server or network
access. Authorization, consent and verification always run through the real
existing mechanisms — nothing is weakened or bypassed for these tests.
"""

from __future__ import annotations

import json

import httpx
from fastapi import FastAPI

from app.services.bill_qa import BillQuestionService
from app.services.caregiver import CaregiverShareStore, CaregiverSummaryService
from app.services.ollama_client import OllamaChatClient
from app.services.personalization import PersonalizationService

SUNRISE_BILL = "SUN-2026-004512"
SUNRISE_CODE = "DEMO1234"


def ollama_answer(text: str) -> OllamaChatClient:
    """A client whose transport returns ``text`` as one well-formed completion."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps({"message": {"content": text}}).encode(),
            request=request,
        )

    return OllamaChatClient(
        base_url="http://localhost:11434",
        model="qwen3:1.7b",
        timeout_seconds=10.0,
        max_output_chars=2000,
        transport=httpx.MockTransport(handler),
    )


def failing_client(exc: Exception) -> OllamaChatClient:
    """A client whose transport raises ``exc`` (timeout/unreachable)."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return OllamaChatClient(
        base_url="http://localhost:11434",
        model="qwen3:1.7b",
        timeout_seconds=10.0,
        max_output_chars=2000,
        transport=httpx.MockTransport(handler),
    )


def unreachable_client() -> OllamaChatClient:
    """The local server is down (connection refused)."""

    return failing_client(httpx.ConnectError("connection refused"))


def timed_out_client() -> OllamaChatClient:
    """The local server accepted but did not answer in time."""

    return failing_client(httpx.ReadTimeout("timed out"))


def install_question_service(
    app: FastAPI, answer: str | OllamaChatClient, *, max_answer_chars: int = 800
) -> None:
    client = ollama_answer(answer) if isinstance(answer, str) else answer
    app.state.question_service = BillQuestionService(client, max_answer_chars=max_answer_chars)


def install_personalization_service(
    app: FastAPI, answer: str | OllamaChatClient, *, max_chars: int = 900
) -> None:
    client = ollama_answer(answer) if isinstance(answer, str) else answer
    app.state.personalization_service = PersonalizationService(client, max_chars=max_chars)


def install_caregiver_service(
    app: FastAPI, answer: str | OllamaChatClient, *, max_chars: int = 900
) -> None:
    client = ollama_answer(answer) if isinstance(answer, str) else answer
    app.state.caregiver_summary_service = CaregiverSummaryService(client, max_chars=max_chars)


def install_share_store(app: FastAPI, store: CaregiverShareStore) -> None:
    app.state.caregiver_share_store = store


async def verify_bill(
    client, session_id: str, bill_number: str = SUNRISE_BILL, code: str = SUNRISE_CODE
) -> str:
    """Identify + verify one fictional bill through the real API flow."""

    ident = await client.post(
        "/api/v1/identifications",
        json={"session_id": session_id, "bill_number": bill_number},
    )
    assert ident.status_code == 200, ident.text
    identification_id = ident.json()["identification_id"]
    verified = await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": code},
    )
    assert verified.status_code == 200, verified.text
    return identification_id


async def verified_bill(client) -> tuple[str, str]:
    """A consented session plus a verified Sunrise bill."""

    from tests.conftest import create_consented_session

    session_id = await create_consented_session(client)
    identification_id = await verify_bill(client, session_id)
    return session_id, identification_id


async def post_question(client, identification_id: str, session_id: str, **body) -> httpx.Response:
    payload = {
        "question": "What is the total amount on my bill?",
        "language": "en",
        "ai_consent": True,
        **body,
    }
    return await client.post(
        f"/api/v1/verified-bills/{identification_id}/questions",
        json=payload,
        headers={"X-Session-ID": session_id},
    )


async def post_personalized(
    client, identification_id: str, session_id: str, **body
) -> httpx.Response:
    payload = {"mode": "simple", "language": "en", "ai_consent": True, **body}
    return await client.post(
        f"/api/v1/verified-bills/{identification_id}/personalized-explanation",
        json=payload,
        headers={"X-Session-ID": session_id},
    )


async def create_share(client, identification_id: str, session_id: str, **body) -> httpx.Response:
    payload = {"language": "en", "consent_caregiver_sharing": True, **body}
    return await client.post(
        f"/api/v1/verified-bills/{identification_id}/caregiver-share",
        json=payload,
        headers={"X-Session-ID": session_id},
    )


async def get_summary(client, identification_id: str, share_code: str, **params) -> httpx.Response:
    return await client.get(
        f"/api/v1/verified-bills/{identification_id}/caregiver-summary",
        params=params,
        headers={"X-Caregiver-Share-Code": share_code},
    )
