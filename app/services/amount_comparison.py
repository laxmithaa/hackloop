"""Careful, non-guessing comparison of uploaded amounts against records.

Everything here works in integer minor units (hundredths of a rupee) or
:class:`decimal.Decimal` — binary floats never touch a monetary value.

Only *labelled* amounts participate in a comparison (``Total Amount: …``,
``Amount Payable: …``). A bare ``Rs. 123.45`` has no reliably identifiable
meaning, so it is recorded but never compared. OCR output is unverified input:
a comparison can report the absence of evidence, but never invents a match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.services.records import BillRecord

LABEL_TOTAL = "total"
LABEL_PATIENT_PAYABLE = "patient_payable"

#: Comparison outcomes. ``amounts_differ``, ``matched`` and the evidence
#: states are deliberately kept apart from technical failures elsewhere.
COMPARISON_MATCHED = "matched"
COMPARISON_AMOUNTS_DIFFER = "amounts_differ"
COMPARISON_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
COMPARISON_NO_UPLOADED_IMAGE = "no_uploaded_image"

#: A labelled amount must precede its value on the same (space-joined) OCR
#: line. The rupee/``Rs.`` prefix is consumed so it cannot be mistaken for the
#: label's value; ``INR`` without a label stays unlabelled.
_TOTAL_LABEL = (
    r"(?i)\b(?:grand\s+total|total\s+amount|bill\s+total|total)\b\s*[:\-]?\s*"
    r"(?:₹\s*)?(?:rs\.?\s*)?(?:₹\s*)?"
)
_PAYABLE_LABEL = (
    r"(?i)\b(?:amount\s+payable|patient\s+payable|payable\s+amount|amount\s+due|"
    r"amount\s+paid|balance\s+due|payable|due)\b\s*[:\-]?\s*"
    r"(?:₹\s*)?(?:rs\.?\s*)?(?:₹\s*)?"
)
_MONEY = r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)"

_TOTAL_LABELLED = re.compile(_TOTAL_LABEL + _MONEY)
_PAYABLE_LABELLED = re.compile(_PAYABLE_LABEL + _MONEY)


class AmbiguousAmountError(ValueError):
    """Raised when a monetary string cannot be parsed without guessing."""


@dataclass(frozen=True)
class LabelledAmount:
    """One labelled monetary candidate. ``raw`` always keeps the OCR text."""

    label: str
    raw: str
    minor_units: int


@dataclass(frozen=True)
class ComparisonResult:
    """Outcome of comparing uploaded candidates against the fictional record."""

    status: str
    message: str


def parse_minor_units(raw: str) -> int:
    """Convert ``12,480.00``-shaped text into integer hundredths exactly.

    Validation is strict: comma groups must be groups of exactly three digits
    after the leading group, and fractions have at most two digits. Anything
    else is rejected instead of guessed at; leading/trailing commas and
    non-digit placeholders never parse.
    """

    text = raw.strip()
    if not text or not re.fullmatch(r"[0-9][0-9,]*(\.[0-9]{1,2})?", text):
        raise AmbiguousAmountError(f"Unparsable amount format: {text!r}")

    integer_part, _, fraction = text.partition(".")
    groups = integer_part.split(",")
    if any(group == "" for group in groups):
        raise AmbiguousAmountError(f"Ambiguous comma use in amount: {text!r}")
    if any(len(group) != 3 for group in groups[1:]):
        raise AmbiguousAmountError(f"Ambiguous comma grouping in amount: {text!r}")

    try:
        value = Decimal("".join(groups) or "0")
        if fraction:
            value += Decimal(f"0.{fraction}")
    except InvalidOperation as exc:  # pragma: no cover - regex already guards
        raise AmbiguousAmountError(f"Unparsable amount format: {text!r}") from exc

    minor_units = value * 100
    if minor_units != minor_units.to_integral_value():
        raise AmbiguousAmountError(f"More than two decimal places: {text!r}")
    return int(minor_units)


def extract_labelled_amounts(ocr_text: str) -> list[LabelledAmount]:
    """Pull labelled monetary candidates out of raw OCR text.

    Unlabelled numbers are ignored here; the plain (unlabelled) extraction in
    ``app.services.identification`` still records them, but a comparison may
    only consume values whose meaning is identifiable.
    """

    results: list[LabelledAmount] = []
    for pattern, label in (
        (_TOTAL_LABELLED, LABEL_TOTAL),
        (_PAYABLE_LABELLED, LABEL_PATIENT_PAYABLE),
    ):
        for match in pattern.finditer(ocr_text):
            raw = match.group(1)
            try:
                minor_units = parse_minor_units(raw)
            except AmbiguousAmountError:
                # An unparsable format is not a compare-worthy candidate.
                continue
            results.append(LabelledAmount(label=label, raw=raw, minor_units=minor_units))
    return results


def _record_amount_for(bill: BillRecord, label: str) -> int:
    """Map a label to the corresponding field of the (unrenamed) record."""

    if label == LABEL_TOTAL:
        return bill.total_amount_cents
    return bill.patient_payable_cents


def compare_uploaded_amounts(
    bill: BillRecord,
    labelled: list[LabelledAmount] | None,
    *,
    uploaded: bool,
) -> ComparisonResult:
    """Compare labelled uploaded candidates with the record. Never guesses.

    ``uploaded=False`` means the identification came from manual bill-number
    entry, so no uploaded-bill comparison has occurred at all.
    """

    if not uploaded:
        return ComparisonResult(
            status=COMPARISON_NO_UPLOADED_IMAGE,
            message=(
                "No bill image was uploaded, so there is nothing to compare. "
                "Upload a photo of the printed bill to compare amounts."
            ),
        )
    if not labelled:
        return ComparisonResult(
            status=COMPARISON_INSUFFICIENT_EVIDENCE,
            message=(
                "We could not read clearly labelled amounts from the uploaded bill, "
                "so no comparison was performed. The verification itself succeeded."
            ),
        )

    # Reliability first: if one label is reported twice with different values
    # the OCR text is contradictory, and neither value may be trusted.
    by_label: dict[str, LabelledAmount] = {}
    for amount in labelled:
        if amount.label in by_label and by_label[amount.label].minor_units != amount.minor_units:
            return ComparisonResult(
                status=COMPARISON_INSUFFICIENT_EVIDENCE,
                message=(
                    "We read conflicting amounts for the same label on the uploaded bill, "
                    "so no comparison was performed. Please upload a clearer photo."
                ),
            )
        by_label[amount.label] = amount

    mismatches: list[str] = []
    evaluated: list[str] = []
    for label, amount in by_label.items():
        recorded = _record_amount_for(bill, label)
        evaluated.append(label)
        if amount.minor_units != recorded:
            mismatches.append(label)

    match_count = len(evaluated) - len(mismatches)
    if mismatches:
        return ComparisonResult(
            status=COMPARISON_AMOUNTS_DIFFER,
            message=(
                "Some amounts we read from your uploaded bill differ from our records for "
                "this entry. This does not tell us which side is wrong. We recommend "
                "contacting human support before you pay."
            ),
        )
    return ComparisonResult(
        status=COMPARISON_MATCHED,
        message=(
            "The labelled amount(s) we could read from your upload match the recorded "
            f"total/payable values ({match_count} compared)."
        ),
    )


def format_minor_units(minor_units: int) -> str:
    """Exact two-decimal rendering of minor units using :class:`Decimal`."""

    value = (Decimal(minor_units) / Decimal(100)).quantize(Decimal("0.01"))
    return f"{value:.2f}"
