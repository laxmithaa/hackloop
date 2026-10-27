"""Schemas for grounded bill Q&A (Phase 9, Part A).

Request rules:

- The only inputs are the question text, the response language and explicit
  consent to local AI processing. Amounts, dates, insurance values,
  verification state or an arbitrary record can never be supplied: the
  server resolves all of them from the authorized session.
- The question is bounded in length and stripped of control characters before
  it can reach a prompt.

Response rules: the answer carries full provenance (``source``/``status``) so
a client can distinguish validated model prose, deterministic record text,
an approved glossary definition and a policy refusal. No raw record and no
conversation transcript is returned.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Same language contract as the Phase 8 explanation feature.
QuestionLanguage = Literal["en", "hi", "kn"]

#: ``generated`` = validated local-model prose; ``fallback`` = deterministic
#: answer after model failure/rejection; ``glossary`` = approved definition;
#: ``record`` = deterministic text for a figure the record does not contain;
#: ``policy`` = fixed refusal.
QuestionSource = Literal["generated", "fallback", "glossary", "record", "policy"]

QuestionStatus = Literal["answered", "refused"]


class BillQuestionRequest(BaseModel):
    """Request body for ``POST .../verified-bills/{identification_id}/questions``.

    The session identifier travels in the ``X-Session-ID`` header, exactly as
    on the protected verified-bill and explanation endpoints.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "question": "What does the outstanding balance mean?",
                "language": "en",
                "ai_consent": True,
            }
        },
    )

    question: str = Field(
        min_length=3,
        max_length=1000,
        description=(
            "One follow-up question about this verified bill. Bounded in length; "
            "treated as untrusted data, never as instructions."
        ),
    )
    language: QuestionLanguage = Field(
        default="en",
        description="Answer language: English (en), Hindi (hi) or Kannada (kn).",
    )
    ai_consent: Literal[True] = Field(
        description=(
            "Explicit, request-specific consent to local AI processing for this "
            "question. Must be true; the request is refused otherwise."
        )
    )

    @field_validator("question")
    @classmethod
    def _question(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("question must contain at least 3 characters.")
        if any(ord(character) < 32 for character in cleaned):
            raise ValueError("question must not contain control characters.")
        return cleaned


class BillQuestionResponse(BaseModel):
    """One validated answer with provenance. Never includes the raw record."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "language": "en",
                "question_intent": "total_amount",
                "status": "answered",
                "source": "generated",
                "answer": "The recorded total bill amount is Rs 12480.00.",
                "fallback_reason": None,
                "questions_remaining": 9,
                "generated_at": "2026-10-27T09:15:00Z",
            }
        }
    )

    identification_id: str
    language: QuestionLanguage
    question_intent: str = Field(
        description=(
            "How the backend classified the question (e.g. 'total_amount', "
            "'glossary', 'medical_advice'). Classification happens before any "
            "generation."
        )
    )
    status: QuestionStatus
    source: QuestionSource
    answer: str = Field(description="Patient-facing answer text. Never authoritative for amounts.")
    fallback_reason: str | None = Field(
        default=None,
        description=(
            "Why deterministic text replaced generated prose (e.g. the local "
            "model was unavailable, or its output failed validation)."
        ),
    )
    questions_remaining: int = Field(
        ge=0,
        description="Follow-up questions this session may still ask (server-enforced).",
    )
    generated_at: datetime
