"""Local GenAI bill-explanation endpoint (Phase 8).

``POST /api/v1/verified-bills/{identification_id}/explanation``

Authorization order mirrors the protected verified-bill GET exactly (the
same helpers are reused, not duplicated): a live session with granted
consent, then proof that *this session* verified *this identification*. On
top of that sit the Phase 8 requirements: explicit, request-specific consent
to local AI processing, and an authorised bill record.

Trusted facts are assembled exclusively from backend services; the local
Ollama model receives only a whitelisted summary and its prose is validated
before it is returned. Any model failure degrades to deterministic text —
never to an API error, and never to client-supplied data.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request

from app.core.errors import IdentificationNotVerifiableError
from app.schemas.errors import ErrorResponse
from app.schemas.explanations import BillExplanationResponse, ExplanationRequest
from app.schemas.verification import validate_session_id_format
from app.services.bill_facts import build_trusted_facts
from app.services.explanations import ExplanationService
from app.services.verification import VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Explanations"])


def _error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        403: doc(
            403,
            "Consent withdrawn, or access-code verification still required.",
        ),
        404: doc(404, "Unknown/expired session or no such identification in this session."),
        422: doc(422, "Request validation failure (unsupported language or missing AI consent)."),
        500: doc(500, "Unexpected server error; internals never leak."),
    }


@router.post(
    "/verified-bills/{identification_id}/explanation",
    response_model=BillExplanationResponse,
    summary="Explain a verified bill (local AI layer, protected)",
    description=(
        "Returns a plain-language explanation of a successfully verified bill in "
        "English, Hindi or Kannada, produced by the locally configured Ollama "
        "model (or by deterministic backend text when the model is unavailable "
        "or unsafe). Requires the session that verified the identification "
        "(X-Session-ID header), granted consent, an explicit request-level AI "
        "processing consent, and a successfully verified bill. Generated prose "
        "is non-authoritative: trusted amounts, dates and comparison outcomes "
        "always travel in the separate, server-owned `facts` field. Financial "
        "facts in the prose are validated against the record; unsupported "
        "financial claims cause the fallback text to be used instead."
    ),
    operation_id="explain_verified_bill",
    responses=_error_docs(),
)
async def explain_verified_bill(
    identification_id: str,
    payload: ExplanationRequest,
    request: Request,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    from app.api.v1.routes.verification import _authorization_guard, _consented_session

    validate_session_id_format(x_session_id)
    session = _consented_session(request, x_session_id)
    verification, identification = _authorization_guard(request, session, identification_id)

    service: VerificationService = request.app.state.verification_service
    comparison = verification.comparison
    # Resolve the (single, registered) bill behind the verification; this is
    # also the fail-closed guarantee that facts never come from client input.
    try:
        facts_out, model_facts = build_trusted_facts(service, identification, comparison)
    except IdentificationNotVerifiableError:  # registry entry removed/misconfigured
        raise

    explanation_service: ExplanationService = request.app.state.explanation_service
    outcome = await explanation_service.explain(model_facts, payload.language)

    return BillExplanationResponse(
        identification_id=identification.identification_id,
        language=payload.language,
        source=outcome.source,
        explanation=outcome.text,
        fallback_reason=outcome.reason,
        facts=facts_out,
        generated_at=datetime.now(UTC),
    )
