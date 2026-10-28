"""Bill identification endpoints (``/api/v1/identifications``)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.config import Settings
from app.core.errors import ConsentRequiredError
from app.schemas.errors import ErrorResponse
from app.schemas.identifications import IdentificationResponse, ManualIdentificationRequest
from app.services.identification import (
    STATUS_ACCESS_CODE_REQUIRED,
    extract_candidates,
    resolve_from_ocr,
    resolve_manual,
)
from app.services.image_validation import read_upload_limited, validate_image
from app.services.records import normalise_bill_number
from app.services.session_store import CONSENT_GRANTED, IdentificationRecord, SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Identification"], prefix="/identifications")


def _contract_error_docs() -> dict[int | str, dict[str, Any]]:
    """OpenAPI response docs pointing at the standard error envelope."""

    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        400: doc(400, "Unsupported image format or image validation failure."),
        403: doc(403, "Consent is required (or was withdrawn) for this session."),
        404: doc(404, "Unknown or expired session identifier."),
        413: doc(413, "The uploaded image exceeds the configured size limit."),
        422: doc(422, "Request validation failure."),
        500: doc(500, "The OCR engine failed while processing the image."),
        503: doc(503, "The OCR engine is unavailable on this server."),
    }


def determine_session_with_consent(request: Request, session_id: str):
    """Shared guard: the session must exist, be live, and have granted consent."""

    store: SessionStore = request.app.state.session_store
    session = store.get(session_id)  # raises 404 for unknown/expired sessions
    if session.consent_decision != CONSENT_GRANTED:
        raise ConsentRequiredError(
            "Record patient consent (or re-record it after withdrawal) before bill identification."
        )
    return session


def _record_and_respond(
    request: Request,
    session,
    *,
    outcome,
) -> IdentificationResponse:
    store: SessionStore = request.app.state.session_store
    record = IdentificationRecord(
        identification_id=uuid4().hex,
        created_at=datetime.now(UTC),
        status=outcome.status,
        hospital_id=outcome.hospital.hospital_id if outcome.hospital else None,
        hospital_name=outcome.hospital.name if outcome.hospital else None,
        bill_number=outcome.bill_number,
        extracted=(
            {
                "bill_date_raw": [outcome.extracted.bill_date_raw],
                "amounts": outcome.extracted.amounts,
                "labelled_amounts": [
                    {
                        "label": labelled.label,
                        "raw": labelled.raw,
                        "minor_units": labelled.minor_units,
                    }
                    for labelled in outcome.extracted.labelled_amounts
                ],
            }
            if outcome.extracted is not None
            else {}
        ),
    )
    store.add_identification(session, record)

    # The challenge lifetime starts at identification time (defined starting
    # point) for every result that requires an access code.
    if outcome.status == STATUS_ACCESS_CODE_REQUIRED:
        _create_challenge_for(request, session, record, outcome)

    logger.info(
        "identification completed status=%s hospital_known=%s bytes_only_meta=yes",
        outcome.status,
        outcome.hospital is not None,
    )
    return IdentificationResponse(
        identification_id=record.identification_id,
        status=outcome.status,
        hospital_name=record.hospital_name,
        bill_number=record.bill_number,
        message=outcome.message,
        next_action=outcome.next_action,
    )


def _create_challenge_for(request: Request, session, record, outcome) -> None:
    """Create the verification challenge for a successful identification."""

    bill = request.app.state.records.find_bill_in_hospital(
        normalise_bill_number(outcome.bill_number or ""), outcome.hospital.hospital_id
    )
    if bill is not None:  # else: verification of this id fails closed later
        request.app.state.verification_service.create_challenge(
            session, record, bill_id=bill.bill_id
        )


@router.post(
    "",
    response_model=IdentificationResponse,
    summary="Identify a bill manually",
    description=(
        "Identifies a bill from a typed bill number, optionally narrowed by a hospital "
        "name or code to resolve ambiguity. Requires an active session with granted "
        "consent. The response never contains financial amounts."
    ),
    operation_id="identify_bill_manually",
    responses=_contract_error_docs(),
)
async def identify_bill_manually(payload: ManualIdentificationRequest, request: Request):
    session = determine_session_with_consent(request, payload.session_id)
    outcome = resolve_manual(
        request.app.state.records,
        bill_number=payload.bill_number,
        hospital_identifier=payload.hospital_identifier,
    )
    return _record_and_respond(request, session, outcome=outcome)


@router.post(
    "/upload",
    response_model=IdentificationResponse,
    summary="Identify a bill from a photo",
    description=(
        "Accepts a JPEG, PNG or WebP photo of a bill as multipart/form-data, validates "
        "it, runs local (non-generative) OCR and attempts identification. Requires an "
        "active session with granted consent. Images are processed in memory only and "
        "never stored; OCR output is treated as unverified. The response never "
        "contains financial amounts."
    ),
    operation_id="identify_bill_from_image",
    responses=_contract_error_docs(),
)
async def identify_bill_from_image(
    request: Request,
    session_id: Annotated[str, Form(min_length=20, max_length=64)],
    file: Annotated[UploadFile, File(description="Bill photo (JPEG, PNG or WebP).")],
):
    settings: Settings = request.app.state.settings
    session = determine_session_with_consent(request, session_id)

    data = await read_upload_limited(file, settings.bill_upload_max_size_bytes)
    image = validate_image(data, max_dimension_px=settings.image_max_dimension_px)

    ocr_result = request.app.state.ocr_adapter.extract_image_text(image)

    candidates = extract_candidates(ocr_result.text)
    low_confidence = (
        ocr_result.mean_confidence is not None
        and ocr_result.mean_confidence < settings.ocr_low_confidence_threshold
    )
    text_matched_hospitals = request.app.state.records.match_hospitals(ocr_result.text)
    outcome = resolve_from_ocr(
        request.app.state.records,
        candidates=candidates,
        text_matched_hospitals=text_matched_hospitals,
        low_confidence=low_confidence,
        empty_text=not ocr_result.text.strip(),
    )
    return _record_and_respond(request, session, outcome=outcome)
