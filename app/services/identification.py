"""Bill-identification business logic, independent of the HTTP layer.

Both the manual (bill number) and OCR (image) flows funnel through this module.
It consumes only the :class:`~app.services.records.BillRecordAccess` interface,
so a later persistence phase can replace the storage without touching the API
or these rules.

OCR text is unverified input: candidate extraction reads it for bill numbers,
dates and amounts, but the final outcome is always decided by a registry match.
No monetary value or date ever reaches an identification response; extracted
amounts stay in the server-side identification record for a later phase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from app.services.amount_comparison import LabelledAmount, extract_labelled_amounts
from app.services.records import BillRecordAccess, HospitalRecord, normalise_bill_number

#: Outcomes reported in identification responses (business layer).
STATUS_ACCESS_CODE_REQUIRED = "access_code_required"
STATUS_BILL_NOT_FOUND = "bill_not_found"
STATUS_HOSPITAL_NOT_REGISTERED = "hospital_not_registered"
STATUS_UNREADABLE_IMAGE = "unreadable_image"
STATUS_BILL_NUMBER_NOT_FOUND = "bill_number_not_found"
STATUS_AMBIGUOUS_HOSPITAL = "ambiguous_hospital"

#: Next actions. One outcome maps to exactly one action; the schema pins them.
NEXT_VERIFY_ACCESS_CODE = "verify_access_code"
NEXT_ENTER_MANUALLY = "enter_bill_number_manually"
NEXT_PROVIDE_HOSPITAL = "provide_hospital_identifier"
NEXT_CHECK_BILL_NUMBER = "check_bill_number"
NEXT_CHECK_HOSPITAL_NAME = "check_hospital_name"

#: Anchored "BILL NO:" patterns first, then a structural fallback for clearly
#: printed bill numbers such as SUN-2026-004512.
_BILL_LABELLED = re.compile(
    r"(?i)\bbill\s*(?:no|number|id)\.?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9/.\- ]{2,24})"
)
#: English words that regularly follow a bill number on the same OCR line
#: ("…SUN-2026-004512 Date of …"). Used to trim label captures; the registry
#: still decides everything, these are only unverified candidates.
_BILL_TAIL_NOISE = re.compile(
    r"(?i)\s+(?:date|due|invoice|issued?|total|amount|balance|payable|patient|and|of|bill)\b.*$"
)
_BILL_STRUCTURAL = re.compile(r"\b([A-Z]{2,4}[-]?\d{2,4}[-]?\d{3,6})\b")
_DATE_LABELLED = re.compile(
    r"(?i)\b(?:bill\s*)?date\s*(?:of\s*issue)?\.?\s*[:\-]?\s*"
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})"
)
_AMOUNT = re.compile(
    r"(?i)(?:\b(?:total|amount|payable|inr)\b|\brs\.|₹)\s*[:\-]?\s*"
    r"₹?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
)


@dataclass(frozen=True)
class ExtractedCandidates:
    """Raw, unverified candidates from OCR text. Never serialised to responses.

    ``amounts`` keeps every monetary string; ``labelled_amounts`` keeps only
    values whose label maps reliably to a record field (used by the Phase 3
    comparison).
    """

    bill_number: str | None = None
    bill_date_raw: str | None = None
    amounts: list[str] = field(default_factory=list)
    labelled_amounts: list[LabelledAmount] = field(default_factory=list)


@dataclass(frozen=True)
class IdentificationOutcome:
    """The result of one identification attempt, safe to expose to a client."""

    status: str
    next_action: str
    message: str
    hospital: HospitalRecord | None = None
    bill_number: str | None = None
    extracted: ExtractedCandidates | None = None


def _outcome_for_bill(
    bill_access: BillRecordAccess,
    *,
    bill_number_input: str,
    hospital: HospitalRecord | None,
) -> IdentificationOutcome:
    """Resolve a normalised bill number against the registry."""

    normalised = normalise_bill_number(bill_number_input)
    if hospital is not None:
        bill = bill_access.find_bill_in_hospital(normalised, hospital.hospital_id)
        if bill is None:
            return IdentificationOutcome(
                status=STATUS_BILL_NOT_FOUND,
                next_action=NEXT_CHECK_BILL_NUMBER,
                message=(
                    f"This bill number was not found at {hospital.name}. "
                    "Please check the bill number and try again."
                ),
                hospital=hospital,
                bill_number=normalised,
            )
        return IdentificationOutcome(
            status=STATUS_ACCESS_CODE_REQUIRED,
            next_action=NEXT_VERIFY_ACCESS_CODE,
            message=(
                f"We found a matching bill at {hospital.name}. Next, verify your access code."
            ),
            hospital=hospital,
            bill_number=bill.bill_number,
        )

    bills = bill_access.find_bills_anywhere(normalised)
    if not bills:
        return IdentificationOutcome(
            status=STATUS_BILL_NOT_FOUND,
            next_action=NEXT_CHECK_BILL_NUMBER,
            message=("This bill number was not found. Please check the bill number and try again."),
            bill_number=normalised,
        )
    if len(bills) > 1:
        return IdentificationOutcome(
            status=STATUS_AMBIGUOUS_HOSPITAL,
            next_action=NEXT_PROVIDE_HOSPITAL,
            message=(
                "This bill number exists at more than one registered hospital. "
                "Please add the hospital name or code."
            ),
            bill_number=normalised,
        )
    bill = bills[0]
    # Look the hospital up through the same access interface instead of guessing.
    hospital_record = bill_access.get_hospital(bill.hospital_id)
    if hospital_record is not None:
        return IdentificationOutcome(
            status=STATUS_ACCESS_CODE_REQUIRED,
            next_action=NEXT_VERIFY_ACCESS_CODE,
            message=(
                f"We found a matching bill at {hospital_record.name}. "
                "Next, verify your access code."
            ),
            hospital=hospital_record,
            bill_number=bill.bill_number,
        )
    # Unreachable with the bundled registry, but never guess if data drifts.
    return IdentificationOutcome(  # pragma: no cover - defensive
        status=STATUS_BILL_NOT_FOUND,
        next_action=NEXT_CHECK_BILL_NUMBER,
        message="This bill number was not found. Please check the bill number and try again.",
        bill_number=normalised,
    )


def resolve_manual(
    bill_access: BillRecordAccess,
    *,
    bill_number: str,
    hospital_identifier: str | None = None,
) -> IdentificationOutcome:
    """Identify a bill from a manually typed bill number (and optional hospital)."""

    cleaned = hospital_identifier.strip() if hospital_identifier else None
    hospital: HospitalRecord | None = None
    if cleaned:
        matched = bill_access.match_hospitals(cleaned)
        if not matched:
            return IdentificationOutcome(
                status=STATUS_HOSPITAL_NOT_REGISTERED,
                next_action=NEXT_CHECK_HOSPITAL_NAME,
                message=(
                    "We could not find this hospital in our registered list. "
                    "Please check the hospital name or code."
                ),
            )
        if len(matched) > 1:
            return IdentificationOutcome(
                status=STATUS_AMBIGUOUS_HOSPITAL,
                next_action=NEXT_PROVIDE_HOSPITAL,
                message="This hospital identifier matched more than one registered hospital.",
            )
        hospital = matched[0]
    return _outcome_for_bill(bill_access, bill_number_input=bill_number, hospital=hospital)


def extract_candidates(ocr_text: str) -> ExtractedCandidates:
    """Pull unverified candidate fields out of raw OCR text.

    Reading text here is dictionary-driven matching against known shapes; the
    contents of the image are never executed or followed.
    """

    bill_number: str | None = None
    label_match = _BILL_LABELLED.search(ocr_text)
    if label_match:
        captured = _BILL_TAIL_NOISE.sub("", label_match.group(1)).strip()
        # A clean structural token inside the capture beats a mangled capture
        # (OCR merges the bill line with the following line into one string).
        structural_in_capture = _BILL_STRUCTURAL.search(captured)
        bill_number = (
            structural_in_capture.group(1) if structural_in_capture else captured
        ) or None
    if bill_number is None:
        structural = _BILL_STRUCTURAL.search(ocr_text)
        if structural:
            bill_number = structural.group(1)
    if bill_number is not None:
        normalised = normalise_bill_number(bill_number)
        bill_number = normalised or None

    date_match = _DATE_LABELLED.search(ocr_text)
    amounts = [m.group(1) for m in _AMOUNT.finditer(ocr_text)]
    return ExtractedCandidates(
        bill_number=bill_number,
        bill_date_raw=date_match.group(1) if date_match else None,
        amounts=amounts,
        labelled_amounts=extract_labelled_amounts(ocr_text),
    )


def resolve_from_ocr(
    bill_access: BillRecordAccess,
    *,
    candidates: ExtractedCandidates,
    text_matched_hospitals: list[HospitalRecord],
    low_confidence: bool,
    empty_text: bool,
) -> IdentificationOutcome:
    """Turn OCR output plus a registry into an identification outcome.

    Rules are deliberately conservative:
    - empty text or low-confidence text -> ``unreadable_image`` (never a guess);
    - no bill-number candidate -> ``bill_number_not_found``;
    - several registry hospitals matched -> ``ambiguous_hospital``;
    - an identified-but-unregistered hospital name means the bill number is
      looked up globally instead of pretending the hospital was verified.
    """

    if empty_text or low_confidence:
        message = (
            "We could not read this image clearly enough."
            if empty_text
            else "The text we could read is not reliable enough to identify a bill."
        )
        return IdentificationOutcome(
            status=STATUS_UNREADABLE_IMAGE,
            next_action=NEXT_ENTER_MANUALLY,
            message=(
                f"{message} Please retry with a clearer, well-lit photo of the full bill "
                "or enter the bill number manually."
            ),
        )

    hospital: HospitalRecord | None = None
    if len(text_matched_hospitals) > 1:
        return IdentificationOutcome(
            status=STATUS_AMBIGUOUS_HOSPITAL,
            next_action=NEXT_PROVIDE_HOSPITAL,
            message=(
                "More than one registered hospital may be mentioned in this image. "
                "Please add the hospital name or code."
            ),
        )
    if len(text_matched_hospitals) == 1:
        hospital = text_matched_hospitals[0]

    if candidates.bill_number is None:
        if hospital is None:
            return IdentificationOutcome(
                status=STATUS_UNREADABLE_IMAGE,
                next_action=NEXT_ENTER_MANUALLY,
                message=(
                    "We could not find a hospital or bill number in this image. "
                    "Please retry with a clearer photo of the full bill "
                    "or enter the bill number manually."
                ),
            )
        return IdentificationOutcome(
            status=STATUS_BILL_NUMBER_NOT_FOUND,
            next_action=NEXT_ENTER_MANUALLY,
            message=(
                f"We could read {hospital.name} on the bill but could not find a bill "
                "number. Please enter the bill number manually."
            ),
            hospital=hospital,
        )

    outcome = _outcome_for_bill(
        bill_access, bill_number_input=candidates.bill_number, hospital=hospital
    )
    # Carry the raw OCR candidates onto the final outcome so the server-side
    # identification record keeps dates/amounts for the later verification phase.
    if outcome.extracted is None:
        outcome = replace(outcome, extracted=candidates)
    return outcome
