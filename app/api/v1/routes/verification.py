"""Access-code verification endpoints (``/api/v1``).

- ``POST /api/v1/identifications/{identification_id}/verify``
- ``GET  /api/v1/verified-bills/{identification_id}``

Both require the session identifier (in the JSON body for verify; in the
``X-Session-ID`` header for the GET so the secret id never lands in query
strings that proxies routinely log). Financial values are returned **only**
through the protected GET after a successful verification, from the session
that performed the identification.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request

from app.core.errors import (
    ConsentRequiredError,
    IdentificationNotFoundError,
    VerificationRequiredError,
)
from app.schemas.errors import ErrorResponse
from app.schemas.verification import (
    AccessCodeVerifyRequest,
    ComparisonSummary,
    RecordedAmountOut,
    UploadedAmountOut,
    VerificationResponse,
    VerifiedBillResponse,
    validate_session_id_format,
)
from app.services.amount_comparison import COMPARISON_NO_UPLOADED_IMAGE, format_minor_units
from app.services.session_store import CONSENT_GRANTED, PatientSession
from app.services.verification import VERIFICATION_STATUS_VERIFIED, VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Verification"])


def _contract_error_docs(verify: bool) -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    docs = {
        403: doc(
            403,
            "Verification locked, consent withdrawn, or verification still required.",
        ),
        404: doc(404, "Unknown/expired session or unknown identification in this session."),
        409: doc(409, "The identification cannot be verified (does not require a code)."),
        410: doc(410, "The verification challenge has expired and must be re-created."),
        422: doc(422, "Request validation failure."),
    }
    if verify:
        docs[401] = doc(401, "The access code is not correct (attempts remain).")
    return docs


def _consented_session(request: Request, session_id: str) -> PatientSession:
    """Live session with granted consent, or the appropriate error."""

    store = request.app.state.session_store
    session = store.get(session_id)  # raises 404 for unknown/expired sessions
    if session.consent_decision != CONSENT_GRANTED:
        raise ConsentRequiredError(
            "Patient consent must remain granted for bill verification and stored bill information."
        )
    return session


def _authorization_guard(request: Request, session: PatientSession, identification_id: str):
    """Enforce that this session verified this identification.

    A valid session id alone, or a verified session plus an unrelated
    identification id, both fail without revealing whether the identification
    exists elsewhere.
    """

    store = request.app.state.session_store
    verification = session.verifications.get(identification_id)
    if verification is None:
        raise VerificationRequiredError()
    identification = store.get_identification(session, identification_id)
    if identification is None:  # pragma: no cover - verified implies stored
        raise IdentificationNotFoundError()
    return verification, identification


@router.post(
    "/identifications/{identification_id}/verify",
    response_model=VerificationResponse,
    summary="Verify a bill's access code",
    description=(
        "Verifies the access code of a previously identified bill. Requires the session "
        "that performed the identification, valid consent, an unlocked and unexpired "
        "challenge, and the correct access code (checked against a stored PBKDF2 digest, "
        "constant-time). At most three failed attempts per challenge; the challenge "
        "expires five minutes after identification. The response never contains "
        "financial amounts."
    ),
    operation_id="verify_access_code",
    responses=_contract_error_docs(verify=True),
)
async def verify_access_code(
    identification_id: str, payload: AccessCodeVerifyRequest, request: Request
):
    session = _consented_session(request, payload.session_id)
    store = request.app.state.session_store
    identification = store.get_identification(session, identification_id)
    if identification is None:
        raise IdentificationNotFoundError()

    verification_service: VerificationService = request.app.state.verification_service
    record, comparison = verification_service.verify(
        session, identification, submitted_code=payload.access_code
    )
    return VerificationResponse(
        identification_id=record.identification_id,
        status=VERIFICATION_STATUS_VERIFIED,
        verified_at=record.verified_at.isoformat(),
        comparison=(
            ComparisonSummary(status=comparison.status, message=comparison.message)
            if comparison
            else None
        ),
    )


@router.get(
    "/verified-bills/{identification_id}",
    response_model=VerifiedBillResponse,
    summary="Read verified bill information (protected)",
    description=(
        "Returns the recorded financial fields of a fictional bill, but only to the "
        "session that verified the corresponding identification, with consent still "
        "granted and while the session is live. The session identifier must be provided "
        "in the `X-Session-ID` header. Uploaded (OCR-derived) amounts, when present, are "
        "included only as non-authoritative comparison information, clearly flagged."
    ),
    operation_id="get_verified_bill",
    responses=_contract_error_docs(verify=False),
)
async def get_verified_bill(
    identification_id: str,
    request: Request,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    validate_session_id_format(x_session_id)
    session = _consented_session(request, x_session_id)
    verification, identification = _authorization_guard(request, session, identification_id)

    service: VerificationService = request.app.state.verification_service
    bill = service.bill_for_identification(identification)
    comparison = verification.comparison

    uploaded_amounts = None
    if comparison and comparison.status != COMPARISON_NO_UPLOADED_IMAGE:
        extracted = identification.extracted or {}
        uploaded_amounts = [
            UploadedAmountOut(
                label=item["label"], value=format_minor_units(int(item["minor_units"]))
            )
            for item in extracted.get("labelled_amounts", [])
            if isinstance(item, dict) and "minor_units" in item
        ]

    return VerifiedBillResponse(
        identification_id=identification.identification_id,
        status=VERIFICATION_STATUS_VERIFIED,
        verified_at=verification.verified_at.isoformat(),
        bill_number=bill.bill_number,
        hospital_name=identification.hospital_name or "",
        bill_date=bill.bill_date,
        amounts={
            "total_amount": RecordedAmountOut(
                label="total",
                value=format_minor_units(bill.total_amount_cents),
                authoritative=True,
            ),
            "patient_payable": RecordedAmountOut(
                label="patient_payable",
                value=format_minor_units(bill.patient_payable_cents),
                authoritative=True,
            ),
        },
        comparison=(
            ComparisonSummary(status=comparison.status, message=comparison.message)
            if comparison
            else None
        ),
        uploaded_amounts=uploaded_amounts,
    )
