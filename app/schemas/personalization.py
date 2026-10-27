"""Schemas for personalised explanations (Phase 9, Part B).

Personalisation changes *presentation*, never facts: the client may choose
one of three approved modes and a language, and nothing else. It cannot send
an explanation to be simplified (the authenticated record is the source) and
it cannot override a financial value.

Term mode is answered from the approved glossary only, so a definition can
never be fabricated at runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.explanations import TrustedBillFactsOut
from app.schemas.questions import QuestionLanguage

#: Approved glossary codes (definitions live in ``app.services.bill_glossary``).
GlossaryTerm = Literal[
    "total_bill_amount",
    "insurance_covered_amount",
    "amount_already_paid",
    "patient_payable",
    "outstanding_balance",
    "bill_verification",
    "amount_discrepancy",
    "co_payment",
]

#: ``simple`` = same facts in easier words; ``short`` = the essentials only;
#: ``term`` = approved definition of one financial term.
PersonalizationMode = Literal["simple", "short", "term"]

#: Provenance of the returned text: model prose (validated), deterministic
#: fallback, or the approved glossary definition.
PersonalizationSource = Literal["generated", "fallback", "glossary"]


class PersonalizationRequest(BaseModel):
    """Request body for ``POST .../personalized-explanation``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "mode": "simple",
                "language": "hi",
                "ai_consent": True,
            }
        },
    )

    mode: PersonalizationMode = Field(
        description=(
            "'simple' rewrites the explanation in easier words, 'short' keeps only "
            "the essentials, 'term' returns the approved glossary definition."
        )
    )
    language: QuestionLanguage = Field(
        default="en",
        description="Output language: English (en), Hindi (hi) or Kannada (kn).",
    )
    term: GlossaryTerm | None = Field(
        default=None,
        description="Required only when mode='term'; must be absent otherwise.",
    )
    ai_consent: Literal[True] = Field(
        description=(
            "Explicit, request-specific consent to local AI processing. Must be "
            "true; the request is refused otherwise."
        )
    )

    @model_validator(mode="after")
    def _term_matches_mode(self) -> PersonalizationRequest:
        if self.mode == "term":
            if self.term is None:
                raise ValueError("term is required when mode='term'.")
        elif self.term is not None:
            raise ValueError("term is only allowed when mode='term'.")
        return self


class PersonalizedExplanationResponse(BaseModel):
    """The rewritten/defined text plus the authoritative facts it must respect."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "language": "en",
                "mode": "simple",
                "term": None,
                "source": "generated",
                "explanation": "Your bill total is Rs 12480.00. You need to pay Rs 6240.00.",
                "fallback_reason": None,
                "facts": {"bill_number": "SUN-2026-004512"},
                "generated_at": "2026-10-27T09:20:00Z",
            }
        }
    )

    identification_id: str
    language: QuestionLanguage
    mode: PersonalizationMode
    term: GlossaryTerm | None = None
    source: PersonalizationSource
    explanation: str = Field(
        description=(
            "Personalised prose or approved definition. Never authoritative: the "
            "amounts it mentions are validated against `facts`."
        )
    )
    fallback_reason: str | None = Field(
        default=None,
        description="Why deterministic text replaced generated prose (if it did).",
    )
    facts: TrustedBillFactsOut = Field(
        description="Server-owned verified facts; the only source of financial values."
    )
    generated_at: datetime
