"""Schemas for the Phase 8 bill-explanation endpoint.

The response always separates trusted facts (server-owned, authoritative)
from generated prose (a local model, non-authoritative). The prose is
described as such in every response so no client can mistake it for record
data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.verification import ComparisonSummary, UploadedAmountOut

#: Language contract for the explanation layer only (help requests keep
#: their own ``en``/``hi``/``mr`` contract; this feature ships Kannada
#: because the local demo audience uses it).
ExplanationLanguage = Literal["en", "hi", "kn"]

#: Where the explanation text came from. ``generated`` means the local model
#: produced prose that passed output validation; ``fallback`` means the
#: deterministic backend text was used instead.
ExplanationSource = Literal["generated", "fallback"]


class ExplanationRequest(BaseModel):
    """Request body for ``POST .../verified-bills/{identification_id}/explanation``.

    The session identifier travels in the ``X-Session-ID`` header (same rule
    as the protected verified-bill GET) so the secret id never lands in
    server logs via URLs.

    ``ai_consent`` must be an explicit ``True``: consent to the *local AI
    processing* of this request, separate from the session's general bill
    processing consent. Requests without it are rejected before anything is
    generated.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language": "kn",
                "ai_consent": True,
            }
        }
    )

    language: ExplanationLanguage = Field(
        description="Language for the explanation: English (en), Hindi (hi) or Kannada (kn)."
    )
    ai_consent: Literal[True] = Field(
        description=(
            "Explicit, request-specific consent to local AI processing of this "
            "verified-bill explanation. Must be true; the call is refused "
            "otherwise."
        )
    )


class TrustedAmountOut(BaseModel):
    """One authoritative amount, repeated from the verified-bill record."""

    label: str = Field(description="'total' or 'patient_payable'.")
    value: str = Field(description="Authoritative amount as an exact two-decimal string.")
    authoritative: Literal[True] = Field(
        description="Always true: this value comes from the verified record."
    )


class TrustedBillFactsOut(BaseModel):
    """Server-owned facts shipped alongside (never inside) generated prose."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bill_number": "SUN-2026-004512",
                "hospital_name": "Sunrise Multispeciality Hospital",
                "bill_date": "2026-03-05",
                "amounts": {
                    "total": {
                        "label": "total",
                        "value": "12480.00",
                        "authoritative": True,
                    }
                },
            }
        }
    )

    bill_number: str
    hospital_name: str
    bill_date: str
    amounts: dict[str, TrustedAmountOut] = Field(
        description="Authoritative amounts keyed by label; always authoritative."
    )
    comparison: ComparisonSummary | None = Field(
        description="Server-side uploaded-amount comparison outcome, if one exists."
    )
    uploaded_amounts: list[UploadedAmountOut] | None = Field(
        description=(
            "OCR-derived (non-authoritative) amounts from the uploaded image, "
            "when present."
        )
    )


class BillExplanationResponse(BaseModel):
    """A bill explanation: model prose or deterministic fallback, plus facts."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "language": "en",
                "source": "generated",
                "explanation": (
                    "Your verified bill from Sunrise Multispeciality Hospital "
                    "shows a recorded total of Rs 12480.00."
                ),
                "fallback_reason": None,
                "facts": {"bill_number": "SUN-2026-004512"},
                "generated_at": "2026-10-25T12:30:00Z",
            }
        }
    )

    identification_id: str
    language: ExplanationLanguage
    source: ExplanationSource
    explanation: str = Field(
        description=(
            "The prose layer: locally generated (validated) text, or the "
            "deterministic fallback. Never authoritative."
        )
    )
    fallback_reason: str | None = Field(
        description=(
            "Why the deterministic fallback was used instead of generated "
            "prose (e.g. the local model was unavailable). None when the "
            "explanation was generated."
        )
    )
    facts: TrustedBillFactsOut = Field(
        description="Trusted, authoritative bill facts read from backend services."
    )
    generated_at: datetime
