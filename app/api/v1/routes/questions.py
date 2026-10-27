"""Grounded AI bill Q&A endpoint (Phase 9, Part A).

``POST /api/v1/verified-bills/{identification_id}/questions``

Authorization mirrors the protected verified-bill and explanation endpoints
(the same helpers are reused):

1. a live session (``X-Session-ID`` header),
2. consent still granted,
3. proof that *this session* verified *this* identification,
4. explicit request-level consent to local AI processing.

Only then is the per-session question budget consumed and the question
classified. Prohibited questions are refused before the model is called; the
model receives a minimal whitelisted summary plus the delimited question and
its answer is validated against the record before it is returned.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request, Response

from app.core.errors import AiQuestionLimitError, QuestionTooLongError
from app.schemas.errors import ErrorResponse
from app.schemas.questions import BillQuestionRequest, BillQuestionResponse
from app.schemas.verification import validate_session_id_format
from app.services.bill_facts import build_trusted_facts
from app.services.bill_qa import BillQuestionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Bill Assistant"])


def _error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        403: doc(
            403,
            "Consent withdrawn, access-code verification still required, or the "
            "identification belongs to another session.",
        ),
        404: doc(404, "Unknown/expired session or no such identification in this session."),
        409: doc(409, "The bill record behind this identification cannot be resolved."),
        422: doc(422, "Request validation failure (unsupported language or missing AI consent)."),
        429: doc(429, "This session has used all of its follow-up questions."),
        500: doc(500, "Unexpected server error; internals never leak."),
    }


@router.post(
    "/verified-bills/{identification_id}/questions",
    response_model=BillQuestionResponse,
    summary="Ask a follow-up question about a verified bill (protected)",
    description=(
        "Answers ONE question about a successfully verified bill, in English, Hindi "
        "or Kannada, using the locally configured Ollama model or deterministic "
        "backend text when the model is unavailable or its output is unsafe.\n\n"
        "The verified record is the only source of financial facts: the request "
        "carries a question, a language and explicit AI-processing consent — never "
        "an amount, date, verification state or record. Questions about medical "
        "care, legal liability, payment decisions or charge correctness, requests "
        "about another patient, and prompt-injection attempts are refused without "
        "consulting the model. Figures the record does not contain (insurance "
        "share, payments made, outstanding balance, due date) are answered as "
        "'not recorded', never estimated.\n\n"
        "Each answer states its `source`: `generated` (validated model prose), "
        "`fallback` (deterministic text after a model failure or rejected output), "
        "`glossary` (approved definition), `record` (deterministic 'not in this "
        "record' text) or `policy` (fixed refusal). The per-session question limit "
        "is enforced here, not by the client."
    ),
    operation_id="ask_verified_bill_question",
    responses=_error_docs(),
)
async def ask_verified_bill_question(
    identification_id: str,
    payload: BillQuestionRequest,
    request: Request,
    response: Response,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    from app.api.v1.routes.verification import _authorization_guard, _consented_session

    validate_session_id_format(x_session_id)
    settings = request.app.state.settings

    # Static bound first: no session/bill information is consulted yet.
    if len(payload.question) > settings.ai_question_max_chars:
        raise QuestionTooLongError(
            f"The question must be at most {settings.ai_question_max_chars} characters."
        )

    session = _consented_session(request, x_session_id)
    verification, identification = _authorization_guard(request, session, identification_id)

    # Trusted facts are resolved *before* the budget is spent, and exclusively
    # from backend services (fail closed if the registry no longer resolves).
    _, facts = build_trusted_facts(
        request.app.state.verification_service, identification, verification.comparison
    )

    remaining = request.app.state.session_store.consume_ai_question(
        session, limit=settings.ai_questions_per_session
    )
    if remaining is None:
        raise AiQuestionLimitError()

    question_service: BillQuestionService = request.app.state.question_service
    outcome = await question_service.answer(facts, payload.question, payload.language)

    # Intent/source/status only: the question text and the answer are never logged.
    logger.info(
        "bill question answered intent=%s source=%s status=%s",
        outcome.intent,
        outcome.source,
        outcome.status,
    )

    response.headers["Cache-Control"] = "no-store"
    return BillQuestionResponse(
        identification_id=identification.identification_id,
        language=payload.language,
        question_intent=outcome.intent,
        status=outcome.status,
        source=outcome.source,
        answer=outcome.text,
        fallback_reason=outcome.reason,
        questions_remaining=remaining,
        generated_at=datetime.now(UTC),
    )
