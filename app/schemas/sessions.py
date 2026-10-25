"""Schemas for session creation and consent endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConsentDecision = Literal["granted", "withdrawn"]


class ConsentState(BaseModel):
    """Current consent state of a session, as reported by the server."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recorded": False,
                "decision": None,
                "policy_version": None,
                "recorded_at": None,
            }
        }
    )

    recorded: bool = Field(description="Whether any consent decision exists on the server.")
    decision: ConsentDecision | None = Field(description="Latest server-validated decision.")
    policy_version: str | None = Field(description="Consent policy version that was accepted.")
    recorded_at: datetime | None = Field(description="When the decision was recorded (UTC).")


class CreateSessionResponse(BaseModel):
    """A newly created temporary patient session."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
                "consent": {
                    "recorded": False,
                    "decision": None,
                    "policy_version": None,
                    "recorded_at": None,
                },
            }
        }
    )

    session_id: str = Field(description="Unpredictable, temporary session identifier.")
    consent: ConsentState


class ConsentRequest(BaseModel):
    """Patient consent, validated on the server — never taken from a checkbox alone."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision": "granted",
                "policy_version": "patient-consent-2026-10-v1",
            }
        }
    )

    decision: Literal["granted"] = Field(description="The consent decision being recorded.")
    policy_version: str = Field(
        min_length=1,
        description="Version of the consent policy the patient accepted. "
        "Must match the server's current policy version.",
    )


class ConsentResponse(BaseModel):
    """Consent state recorded on the server for a session."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
                "decision": "granted",
                "policy_version": "patient-consent-2026-10-v1",
                "recorded_at": "2026-10-25T12:00:00Z",
            }
        }
    )

    session_id: str
    decision: ConsentDecision
    policy_version: str | None
    recorded_at: datetime | None
