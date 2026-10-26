"""Schemas for access-code verification and protected bill information.

Same design rule as the identification schemas: unsuccessful verification
responses contain no financial fields at all. Amounts appear only through the
protected verified-bill endpoint, and uploaded (OCR-derived) amounts are
always explicitly flagged there as non-authoritative.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.amount_comparison import (
    COMPARISON_AMOUNTS_DIFFER,
    COMPARISON_INSUFFICIENT_EVIDENCE,
    COMPARISON_MATCHED,
    COMPARISON_NO_UPLOADED_IMAGE,
)

ComparisonStatus = Literal[
    "matched",
    "amounts_differ",
    "insufficient_evidence",
    "no_uploaded_image",
]

_SESSION_ID_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=")


def validate_session_id_format(value: str) -> str:
    """Shared session-id format validation (strip, alphabet check)."""

    cleaned = value.strip()
    if not cleaned or any(char not in _SESSION_ID_ALPHABET for char in cleaned):
        raise ValueError("session_id is not a valid session identifier.")
    return cleaned


class AccessCodeVerifyRequest(BaseModel):
    """Request body for ``POST /api/v1/identifications/{id}/verify``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
                "access_code": "DEMO1234",
            }
        }
    )

    session_id: str = Field(min_length=20, max_length=64)
    access_code: str = Field(min_length=1, max_length=64)

    @field_validator("session_id")
    @classmethod
    def _session_id(cls, value: str) -> str:
        return validate_session_id_format(value)

    @field_validator("access_code")
    @classmethod
    def _access_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be empty.")
        return cleaned


class ComparisonSummary(BaseModel):
    """Comparison outcome summary (no amounts)."""

    status: ComparisonStatus
    message: str


class VerificationResponse(BaseModel):
    """Successful verification. Still contains no financial values."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "status": "verified",
                "verified_at": "2026-10-25T12:34:56.000000Z",
                "comparison": {
                    "status": "matched",
                    "message": "The labelled amount(s) we could read from your upload "
                    "match the recorded total/payable values (2 compared).",
                },
            }
        }
    )

    identification_id: str
    status: Literal["verified"]
    verified_at: str = Field(description="UTC timestamp of the successful verification (ISO 8601).")
    comparison: ComparisonSummary | None = Field(
        default=None,
        description=(
            "Amount-comparison result when an uploaded bill was identified; ``null`` "
            "for manual identifications."
        ),
    )


class UploadedAmountOut(BaseModel):
    """One uploaded (OCR-derived) amount, explicitly non-authoritative."""

    label: Literal["total", "patient_payable"]
    value: str = Field(description="Human-readable decimal, e.g. '12480.00'.")
    authoritative: Literal[False] = Field(
        default=False, description="Always False: OCR values never override the record."
    )


class RecordedAmountOut(BaseModel):
    """One recorded amount from the fictional (source) record."""

    label: Literal["total", "patient_payable"]
    value: str
    authoritative: Literal[True]


class VerifiedBillResponse(BaseModel):
    """Protected response: financial fields, only after verification."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "status": "verified",
                "verified_at": "2026-10-25T12:34:56.000000Z",
                "bill_number": "SUN-2026-004512",
                "hospital_name": "Sunrise Multispeciality Hospital",
                "bill_date": "2026-03-14",
                "amounts": {
                    "total_amount": {"label": "total", "value": "12480.00", "authoritative": True},
                    "patient_payable": {
                        "label": "patient_payable",
                        "value": "6240.00",
                        "authoritative": True,
                    },
                },
                "comparison": {
                    "status": "matched",
                    "message": "The labelled amount(s) we could read from your upload match "
                    "the recorded total/payable values (2 compared).",
                    "uploaded": [{"label": "total", "value": "12480.00", "authoritative": False}],
                },
            }
        }
    )

    identification_id: str
    status: Literal["verified"]
    verified_at: str
    bill_number: str
    hospital_name: str
    bill_date: str
    amounts: dict[str, RecordedAmountOut]
    comparison: ComparisonSummary | None = None
    uploaded_amounts: list[UploadedAmountOut] | None = Field(
        default=None,
        description=(
            "Amounts read from the uploaded image. Informational only; they are "
            "authoritative=False and never substitute the recorded values."
        ),
    )


#: Re-export so route/docs modules import from one place.
COMPARISON_STATUSES = (
    COMPARISON_MATCHED,
    COMPARISON_AMOUNTS_DIFFER,
    COMPARISON_INSUFFICIENT_EVIDENCE,
    COMPARISON_NO_UPLOADED_IMAGE,
)
