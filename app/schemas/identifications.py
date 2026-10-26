"""Schemas for bill-identification endpoints.

Deliberate design rule: the identification response has no financial field at
all — no amounts, itemised charges, insurance values, patient-payable totals
or due dates. The fields are absent from the schema, not merely ``null``:
financial information is only ever released after access-code verification in
a later phase.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.identification import (
    NEXT_CHECK_BILL_NUMBER,
    NEXT_CHECK_HOSPITAL_NAME,
    NEXT_ENTER_MANUALLY,
    NEXT_PROVIDE_HOSPITAL,
    NEXT_VERIFY_ACCESS_CODE,
    STATUS_ACCESS_CODE_REQUIRED,
    STATUS_AMBIGUOUS_HOSPITAL,
    STATUS_BILL_NOT_FOUND,
    STATUS_BILL_NUMBER_NOT_FOUND,
    STATUS_HOSPITAL_NOT_REGISTERED,
    STATUS_UNREADABLE_IMAGE,
)

IdentificationStatus = Literal[
    "access_code_required",
    "bill_not_found",
    "hospital_not_registered",
    "unreadable_image",
    "bill_number_not_found",
    "ambiguous_hospital",
]

NextAction = Literal[
    "verify_access_code",
    "enter_bill_number_manually",
    "provide_hospital_identifier",
    "check_bill_number",
    "check_hospital_name",
]

_SESSION_ID_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=")


class ManualIdentificationRequest(BaseModel):
    """Request body for ``POST /api/v1/identifications``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
                "bill_number": "SUN-2026-004512",
                "hospital_identifier": None,
            }
        }
    )

    session_id: str = Field(min_length=20, max_length=64)
    bill_number: str = Field(min_length=3, max_length=32)
    hospital_identifier: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(char not in _SESSION_ID_ALPHABET for char in cleaned):
            raise ValueError("session_id is not a valid session identifier.")
        return cleaned

    @field_validator("bill_number", "hospital_identifier")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be empty.")
        return cleaned


class IdentificationResponse(BaseModel):
    """One identification attempt's outcome. Contains no financial fields."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
                "status": "access_code_required",
                "hospital_name": "Sunrise Multispeciality Hospital",
                "bill_number": "SUN-2026-004512",
                "message": "We found a matching bill at Sunrise Multispeciality Hospital. "
                "Next, verify your access code.",
                "next_action": "verify_access_code",
            }
        }
    )

    identification_id: str = Field(description="Correlation id for this identification attempt.")
    status: IdentificationStatus
    hospital_name: str | None = Field(
        description="Candidate hospital name, when the registry can identify one."
    )
    bill_number: str | None = Field(
        description="Candidate bill number, when the registry can identify one."
    )
    message: str = Field(description="Clear, user-facing summary of the outcome.")
    next_action: NextAction


#: Ordering used by field docs; kept here so route modules stay lean.
STATUS_VALUES: Annotated[tuple[str, ...], ""] = (  # pragma: no cover - documentation only
    STATUS_ACCESS_CODE_REQUIRED,
    STATUS_BILL_NOT_FOUND,
    STATUS_HOSPITAL_NOT_REGISTERED,
    STATUS_UNREADABLE_IMAGE,
    STATUS_BILL_NUMBER_NOT_FOUND,
    STATUS_AMBIGUOUS_HOSPITAL,
)
NEXT_ACTION_VALUES = (
    NEXT_VERIFY_ACCESS_CODE,
    NEXT_ENTER_MANUALLY,
    NEXT_PROVIDE_HOSPITAL,
    NEXT_CHECK_BILL_NUMBER,
    NEXT_CHECK_HOSPITAL_NAME,
)
