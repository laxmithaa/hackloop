"""Schemas for the patient help-request (support) workflow — Phase 4.

Design rules carried over from earlier phases:
- Patient-facing responses contain the minimum: ticket id, status, language,
  callback window. No reason echo, no staff data, no financial amounts.
- The single language contract defined here is used by patient and staff
  models; there is no duplicate language schema elsewhere.
- Unsuccessful or unauthenticated responses reveal nothing about the queue.

Callbacks are simulated workflow records only: nothing here plans or claims a
real phone call, SMS, or email.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.verification import validate_session_id_format

#: Supported languages for human support communication. This is the project's
#: one language contract (patient and staff models reference it by name).
SupportedLanguage = Literal["en", "hi", "mr"]

#: Preferred callback windows, including "now".
CallbackWindow = Literal["now", "morning", "afternoon", "evening"]

#: Public (patient-visible) ticket statuses. The state machine itself lives
#: in ``app.services.help_requests``.
HelpTicketStatus = Literal[
    "new",
    "callback_scheduled",
    "contacted",
    "resolved",
]

_REASON_MIN = 5
_REASON_MAX = 2000


class HelpRequestCreate(BaseModel):
    """Request body for ``POST /api/v1/help-requests``.

    ``consent_sharing_confirmed`` must be explicit ``True``: without it the
    request is rejected and no ticket is created.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "language": "mr",
                "callback_window": "evening",
                "reason": "I could not verify my bill and need help understanding it.",
                "consent_sharing_confirmed": True,
            }
        }
    )

    session_id: str = Field(min_length=20, max_length=64)
    identification_id: str = Field(min_length=8, max_length=64)
    language: SupportedLanguage = Field(
        description="Language the patient prefers for the human callback."
    )
    callback_window: CallbackWindow
    reason: str = Field(
        min_length=_REASON_MIN,
        max_length=_REASON_MAX,
        description="Why help is needed. Stored only once; never logged.",
    )
    consent_sharing_confirmed: Literal[True] = Field(
        description=(
            "Must be true: explicit, request-specific consent to share this "
            "help request with the support team."
        ),
    )

    @field_validator("session_id")
    @classmethod
    def _session_id(cls, value: str) -> str:
        return validate_session_id_format(value)

    @field_validator("identification_id")
    @classmethod
    def _identification_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be empty.")
        return cleaned

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        cleaned = " ".join(value.split())  # collapse whitespace runs
        if not cleaned or len(cleaned) < _REASON_MIN:
            raise ValueError(
                f"reason must be at least {_REASON_MIN} non-whitespace characters."
            )
        return cleaned


class HelpTicketResponse(BaseModel):
    """Patient-facing ticket data: the minimum only."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "9f1c0c45e2b84dfdbde2a2d0f9c60b11",
                "status": "new",
                "language": "mr",
                "callback_window": "evening",
            }
        }
    )

    ticket_id: str
    status: HelpTicketStatus
    language: SupportedLanguage
    callback_window: CallbackWindow


class StaffTicketSummary(BaseModel):
    """One row of the support queue (staff only). No financial amounts."""

    ticket_id: str
    status: HelpTicketStatus
    language: SupportedLanguage
    callback_window: CallbackWindow
    created_at: str
    verification_state: str


class StaffTicketDetail(StaffTicketSummary):
    """Full staff-facing detail, including the patient's reason."""

    reason: str
    summary: str


class StaffStatusUpdate(BaseModel):
    """Request body for the staff status transition."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "callback_scheduled"},
        }
    )

    status: HelpTicketStatus
