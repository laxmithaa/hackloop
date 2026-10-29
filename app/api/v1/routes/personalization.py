"""Personalised explanation endpoint (Phase 9, Part B).

``POST /api/v1/verified-bills/{identification_id}/personalized-explanation``

Same authorization chain as the Phase 8 explanation endpoint. The request can
choose only a presentation mode (``simple``, ``short``, ``term``), a language
and the glossary term for ``term`` mode — never a financial value and never an
explanation to be rewritten. ``simple``/``short`` rewrite a deterministic,
record-derived text; ``term`` answers from the approved glossary only.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request, Response

from app.schemas.errors import ErrorResponse
from app.schemas.personalization import (
    PersonalizationRequest,
    PersonalizedExplanationResponse,
)
from app.schemas.verification import validate_session_id_format
from app.services.bill_facts import build_trusted_facts
from app.services.personalization import PersonalizationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Explanations"])


def _error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        403: doc(403, "Consent withdrawn, or access-code verification still required."),
        404: doc(404, "Unknown/expired session or no such identification in this session."),
        409: doc(409, "The bill record behind this identification cannot be resolved."),
        422: doc(
            422,
            "Request validation failure (unsupported mode/language/term or missing AI consent).",
        ),
        500: doc(500, "Unexpected server error; internals never leak."),
    }


@router.post(
    "/verified-bills/{identification_id}/personalized-explanation",
    response_model=PersonalizedExplanationResponse,
    summary="Personalise a verified bill explanation (protected)",
    description=(
        "Returns a simpler or shorter explanation of a successfully verified bill, "
        "or the approved definition of one financial term, in English, Hindi or "
        "Kannada.\n\n"
        "`simple` and `short` rewrite a deterministic explanation built from the "
        "verified record; the locally configured Ollama model receives that approved "
        "text only, and its rewrite must pass monetary/date validation, length and "
        "claim checks before it is returned. `term` never calls the model: it returns "
        "a prewritten glossary definition. Whenever generation fails or produces "
        "unsafe output, deterministic text in the requested language is returned "
        "instead, with `source='fallback'`. The authoritative values always travel "
        "in the separate `facts` field."
    ),
    operation_id="personalize_verified_bill_explanation",
    responses=_error_docs(),
)
async def personalize_verified_bill_explanation(
    identification_id: str,
    payload: PersonalizationRequest,
    request: Request,
    response: Response,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    from app.api.v1.routes.verification import _authorization_guard, _consented_session

    validate_session_id_format(x_session_id)
    session = _consented_session(request, x_session_id)
    verification, identification = _authorization_guard(request, session, identification_id)

    facts_out, facts = build_trusted_facts(
        request.app.state.verification_service, identification, verification.comparison
    )

    service: PersonalizationService = request.app.state.personalization_service
    outcome = await service.personalize(
        facts,
        mode=payload.mode,
        language=payload.language,
        term=payload.term,
    )

    logger.info(
        "personalised explanation mode=%s source=%s",
        payload.mode,
        outcome.source,
    )

    response.headers["Cache-Control"] = "no-store"
    return PersonalizedExplanationResponse(
        identification_id=identification.identification_id,
        language=payload.language,
        mode=payload.mode,
        term=payload.term,
        source=outcome.source,
        explanation=outcome.text,
        fallback_reason=outcome.reason,
        facts=facts_out,
        generated_at=datetime.now(UTC),
    )
