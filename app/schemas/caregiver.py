"""Schemas for caregiver summaries (Phase 9, Part C).

The patient explicitly grants consent to share a *specific* verified bill with
a caregiver and receives a one-time share code. The caregiver presents that
code to read a summary restricted to the fields listed in ``shared_fields``.

Nothing here grants access from a bill identifier alone: without a live share
code (and a still-live session with granted consent) the summary endpoint
answers 403.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.explanations import TrustedBillFactsOut
from app.schemas.questions import QuestionLanguage

#: Every field the caregiver summary may expose. Fixed and auditable: adding a
#: field is a deliberate privacy decision, not a side effect of the record.
CAREGIVER_SHARED_FIELDS: tuple[str, ...] = (
    "hospital_name",
    "bill_number",
    "bill_date",
    "total",
    "patient_payable",
    "verification_status",
    "comparison_status",
)

CaregiverSummarySource = Literal["generated", "fallback"]


class CaregiverShareRequest(BaseModel):
    """Request body for ``POST .../verified-bills/{id}/caregiver-share``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"language": "en", "consent_caregiver_sharing": True}},
    )

    language: QuestionLanguage = Field(
        default="en",
        description="Default language of the caregiver summary (en, hi or kn).",
    )
    consent_caregiver_sharing: Literal[True] = Field(
        description=(
            "Explicit consent to share this verified bill's summary with whoever "
            "holds the returned share code. Must be true."
        )
    )


class CaregiverShareResponse(BaseModel):
    """The created share. ``share_code`` is returned exactly once."""

    share_id: str
    share_code: str = Field(
        description=(
            "Single-use-to-display credential for the caregiver. Store it securely; "
            "the server keeps only a hash and cannot show it again."
        )
    )
    identification_id: str
    language: QuestionLanguage
    expires_at: datetime
    shared_fields: list[str] = Field(description="Fields the caregiver summary may contain.")


class CaregiverShareRevokeResponse(BaseModel):
    """Result of revoking every active share for one bill."""

    identification_id: str
    revoked_shares: int


class CaregiverSummaryResponse(BaseModel):
    """A concise, validated summary for an authorized caregiver."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "language": "en",
                "source": "fallback",
                "summary": (
                    "What you need to know: Sunrise Multispeciality Hospital, bill "
                    "SUN-2026-004512 dated 2026-03-14. Recorded total: Rs 12480.00. "
                    "Recorded amount payable by the patient: Rs 6240.00."
                ),
                "fallback_reason": "ollama_unreachable",
                "verification_status": "verified",
                "facts": {"bill_number": "SUN-2026-004512"},
                "expires_at": "2026-10-27T10:20:00Z",
                "generated_at": "2026-10-27T09:20:00Z",
            }
        }
    )

    identification_id: str
    language: QuestionLanguage
    source: CaregiverSummarySource
    summary: str = Field(
        description=(
            "Short 'What you need to know' text. Amounts are validated against "
            "`facts`; the summary is not authoritative."
        )
    )
    fallback_reason: str | None = None
    verification_status: Literal["verified"] = "verified"
    facts: TrustedBillFactsOut
    expires_at: datetime
    generated_at: datetime
