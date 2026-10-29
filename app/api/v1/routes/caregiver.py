"""Caregiver share and summary endpoints (Phase 9, Part C).

- ``POST   /api/v1/verified-bills/{identification_id}/caregiver-share``
- ``DELETE /api/v1/verified-bills/{identification_id}/caregiver-share``
- ``GET    /api/v1/verified-bills/{identification_id}/caregiver-summary``

The patient (own session, consent granted, verified bill) mints a share and
receives a random code once. The caregiver presents that code in the
``X-Caregiver-Share-Code`` header. Knowing a bill identifier is never enough:
every summary request re-validates the share (live, unexpired, not revoked)
*and* the patient's session, consent and verification. Withdrawn consent,
expired sessions and revoked shares all answer 403 with one generic message,
so no other patient's information is disclosed through errors.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Request, Response

from app.core.errors import (
    CaregiverShareInvalidError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.schemas.caregiver import (
    CAREGIVER_SHARED_FIELDS,
    CaregiverShareRequest,
    CaregiverShareResponse,
    CaregiverShareRevokeResponse,
    CaregiverSummaryResponse,
)
from app.schemas.errors import ErrorResponse
from app.schemas.questions import QuestionLanguage
from app.schemas.verification import validate_session_id_format
from app.services.bill_facts import build_trusted_facts
from app.services.caregiver import CaregiverShareStore, CaregiverSummaryService
from app.services.session_store import CONSENT_GRANTED

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Caregiver"])


def _summary_error_docs() -> dict[int | str, dict[str, Any]]:
    """Docs for the share-code-only endpoint (no session/identification errors)."""

    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        403: doc(
            403,
            "The caregiver share is missing, invalid, expired or revoked, or the "
            "patient's consent/verification no longer holds.",
        ),
        422: doc(422, "Request validation failure (unsupported language)."),
        500: doc(500, "Unexpected server error; internals never leak."),
    }


def _error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        403: doc(
            403,
            "Consent withdrawn, verification still required, or the caregiver share "
            "is missing, expired or revoked.",
        ),
        404: doc(404, "Unknown/expired session or no such identification in this session."),
        409: doc(409, "Too many active caregiver shares for this bill or session."),
        422: doc(422, "Request validation failure (unsupported language or missing consent)."),
        500: doc(500, "Unexpected server error; internals never leak."),
    }


@router.post(
    "/verified-bills/{identification_id}/caregiver-share",
    response_model=CaregiverShareResponse,
    status_code=201,
    summary="Share a verified bill summary with a caregiver (protected)",
    description=(
        "Mints a time-limited caregiver share for one successfully verified bill. "
        "Requires the patient's own session (X-Session-ID header), granted consent, "
        "a verified identification and explicit consent to caregiver sharing. The "
        "share code is returned exactly once; only a hash is stored, and every "
        "summary request re-validates the patient side. Withdrawing consent revokes "
        "all shares minted by the session immediately. State is in memory only and "
        "is lost on restart."
    ),
    operation_id="create_caregiver_share",
    responses=_error_docs(),
)
async def create_caregiver_share(
    identification_id: str,
    payload: CaregiverShareRequest,
    request: Request,
    response: Response,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    from app.api.v1.routes.verification import _authorization_guard, _consented_session

    validate_session_id_format(x_session_id)
    session = _consented_session(request, x_session_id)
    _, identification = _authorization_guard(request, session, identification_id)

    store: CaregiverShareStore = request.app.state.caregiver_share_store
    share, share_code = store.create(
        identification_id=identification.identification_id,
        session_id=session.session_id,
        language=payload.language,
    )
    logger.info(
        "caregiver share issued identification=%s expires_at=%s",
        identification.identification_id,
        share.expires_at.isoformat(),
    )

    response.headers["Cache-Control"] = "no-store"
    return CaregiverShareResponse(
        share_id=share.share_id,
        share_code=share_code,
        identification_id=share.identification_id,
        language=payload.language,
        expires_at=share.expires_at,
        shared_fields=list(CAREGIVER_SHARED_FIELDS),
    )


@router.delete(
    "/verified-bills/{identification_id}/caregiver-share",
    response_model=CaregiverShareRevokeResponse,
    summary="Revoke every caregiver share for a verified bill (protected)",
    description=(
        "Revokes all active caregiver shares for this verified bill. The patient's "
        "own session, granted consent and successful verification are required. "
        "Withdrawing consent already revokes shares automatically; this endpoint is "
        "for revoking sharing while the patient keeps using their session."
    ),
    operation_id="revoke_caregiver_shares",
    responses=_error_docs(),
)
async def revoke_caregiver_shares(
    identification_id: str,
    request: Request,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    from app.api.v1.routes.verification import _authorization_guard, _consented_session

    validate_session_id_format(x_session_id)
    session = _consented_session(request, x_session_id)
    _, identification = _authorization_guard(request, session, identification_id)

    store: CaregiverShareStore = request.app.state.caregiver_share_store
    revoked = store.revoke_identification(identification.identification_id)
    logger.info(
        "caregiver shares revoked identification=%s count=%d",
        identification.identification_id,
        revoked,
    )
    return CaregiverShareRevokeResponse(
        identification_id=identification.identification_id,
        revoked_shares=revoked,
    )


@router.get(
    "/verified-bills/{identification_id}/caregiver-summary",
    response_model=CaregiverSummaryResponse,
    summary="Read a caregiver summary with a share code",
    description=(
        "Returns a short 'What you need to know' summary of a verified bill to the "
        "holder of a live caregiver share code (`X-Caregiver-Share-Code` header). "
        "The summary is restricted to hospital name, bill number/date, recorded "
        "total, recorded patient-payable amount, verification status and the "
        "uploaded-amount comparison outcome. Amounts and dates come from the "
        "verified record; the local model may only re-word a fixed template, and any "
        "failure or unsafe output falls back to that template. Missing figures are "
        "reported as not recorded, never as zero, and the summary never says whether "
        "a charge is correct or whether to pay. English, Hindi and Kannada are "
        "supported; the patient's chosen share language is the default."
    ),
    operation_id="get_caregiver_summary",
    responses=_summary_error_docs(),
)
async def get_caregiver_summary(
    identification_id: str,
    request: Request,
    response: Response,
    x_caregiver_share_code: Annotated[
        str, Header(alias="X-Caregiver-Share-Code", min_length=20, max_length=128)
    ],
    language: Annotated[
        QuestionLanguage | None,
        Query(description="Optional output language; defaults to the share's language."),
    ] = None,
):
    shares: CaregiverShareStore = request.app.state.caregiver_share_store
    share = shares.authorize(identification_id, x_caregiver_share_code)
    if share is None:
        raise CaregiverShareInvalidError()

    # Re-validate the patient side on *every* request: a share is a request
    # grant, not a standing permission.
    session_store = request.app.state.session_store
    try:
        session = session_store.get(share.session_id)
    except (SessionNotFoundError, SessionExpiredError):
        shares.revoke_session(share.session_id)
        raise CaregiverShareInvalidError() from None

    if session.consent_decision != CONSENT_GRANTED:
        shares.revoke_session(session.session_id)
        raise CaregiverShareInvalidError()

    verification = session.verifications.get(share.identification_id)
    identification = session_store.get_identification(session, share.identification_id)
    if verification is None or identification is None:
        shares.revoke_session(session.session_id)
        raise CaregiverShareInvalidError()

    facts_out, facts = build_trusted_facts(
        request.app.state.verification_service, identification, verification.comparison
    )
    # Sharing is restricted to the declared fields. OCR-derived uploaded
    # amounts are not part of them, so they never leave the patient's own view.
    facts_out = facts_out.model_copy(update={"uploaded_amounts": None})
    resolved_language: str = language or share.language

    service: CaregiverSummaryService = request.app.state.caregiver_summary_service
    outcome = await service.summarize(facts, resolved_language)

    logger.info(
        "caregiver summary served language=%s source=%s",
        resolved_language,
        outcome.source,
    )

    response.headers["Cache-Control"] = "no-store"
    return CaregiverSummaryResponse(
        identification_id=identification.identification_id,
        language=resolved_language,
        source=outcome.source,
        summary=outcome.text,
        fallback_reason=outcome.reason,
        facts=facts_out,
        expires_at=share.expires_at,
        generated_at=datetime.now(UTC),
    )
