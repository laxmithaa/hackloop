"""Pydantic v2 models for the database layer.

Money is always a decimal STRING ("50000.00"), never a float. A None amount
means "the hospital record does not provide it"; it is never turned into 0.
"""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

FieldKey = Literal[
    "billTotalAfterDiscounts",
    "insuranceApprovedButNotPaid",
    "insurancePaidOrCredited",
    "patientPayments",
    "printedAmountDue",
]
FIELD_KEYS: tuple[FieldKey, ...] = (
    "billTotalAfterDiscounts",
    "insuranceApprovedButNotPaid",
    "insurancePaidOrCredited",
    "patientPayments",
    "printedAmountDue",
)

MoneyStr = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$")]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


# ----------------------------------------------------------------- lookup
class BillRecord(_Model):
    bill_id: UUID
    hospital_id: UUID
    hospital_name: str
    bill_number: str


class BillLookup(_Model):
    """Identification only. It never carries amounts."""

    outcome: Literal["found", "hospital_not_registered", "bill_not_found"]
    bill: BillRecord | None = None


class VerifiedRecord(_Model):
    bill_id: UUID
    hospital_name: str
    bill_number: str
    currency: str
    bill_date: date | None
    due_date: date | None
    amounts: dict[FieldKey, MoneyStr | None]


# ----------------------------------------------------------- verification
class VerificationSession(_Model):
    session_id: UUID
    bill_id: UUID
    entry_expires_at: datetime
    max_attempts: int


class VerifyResult(_Model):
    status: Literal["ok", "invalid", "locked_out", "expired", "not_found"]
    attempts_left: int | None = None
    # True when repeated failures should hand the patient to a human.
    escalate: bool = False


class IssuedCode(_Model):
    access_code_id: UUID
    code: str  # shown once, to be printed on the bill; only the hash is stored


# --------------------------------------------------------------- callbacks
CallbackTime = Literal["now", "morning", "afternoon", "evening"]
TicketStatus = Literal["new", "callback_scheduled", "contacted", "resolved"]
Triage = Literal["billing_question", "insurance_mismatch", "possible_distress"]
Escalation = Literal[
    "distress",
    "failed_access_codes",
    "requested_human",
    "consent_withdrawn",
    "unsupported_language",
]


class CallbackRequest(BaseModel):
    """What the patient submits. Consent must be literally true."""

    preferred_language: str = Field(min_length=2, max_length=10)
    callback_time: CallbackTime
    reason: str = Field(min_length=3, max_length=1000)
    patient_name: str = Field(min_length=2, max_length=200)
    phone_number: str = Field(pattern=r"^(\+91|0)?[0-9]{10,15}$")
    consent_to_callback: bool

    @field_validator("consent_to_callback")
    @classmethod
    def _consent_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("consent_to_callback must be true")
        return value


class CallbackTicket(_Model):
    ticket_id: UUID
    short_code: str
    status: TicketStatus
    effective_language: str
    created_at: datetime


class TicketSummary(_Model):
    """A row on the support-worker dashboard."""

    ticket_id: UUID
    short_code: str
    status: TicketStatus
    preferred_language: str
    effective_language: str
    callback_time: CallbackTime
    reason: str
    patient_name: str
    phone_number: str
    case_summary: str | None
    triage_suggestion: Triage | None
    triage_final: Triage | None
    escalation_reason: Escalation | None
    assigned_to: UUID | None
    created_at: datetime


class SupportWorker(_Model):
    worker_id: UUID
    name: str
    role: Literal["chw", "counselor"]
    languages: list[str]
