"""Trusted, server-owned bill facts shared by every GenAI layer.

Phase 8 introduced :class:`ExplanationFacts`; Phase 9 reuses it for grounded
Q&A, personalised explanations and caregiver summaries so there is exactly one
definition of "what the model is allowed to know".

Authority rules encoded here:

- Facts are read exclusively from backend services (record registry,
  verification service, amount comparison). A request can name an
  identification and a language; it can never supply an amount, a date, a
  verification state or an arbitrary record.
- ``> = 0`` recorded amounts only; a missing field stays ``None`` and is
  rendered as "not recorded", never as ``0``.
- The comparison outcome and note are copied verbatim from the comparison
  service; nothing here re-interprets them.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.explanations import TrustedAmountOut, TrustedBillFactsOut
from app.schemas.verification import ComparisonSummary, UploadedAmountOut
from app.services.amount_comparison import COMPARISON_NO_UPLOADED_IMAGE, format_minor_units
from app.services.verification import VerificationService


@dataclass(frozen=True)
class ExplanationFacts:
    """The whitelisted, server-owned facts a GenAI layer may talk about.

    The recorded bill currently has only ``total`` and ``patient_payable``;
    the optional fields stay ``None`` so that a feature which needs them must
    say "not recorded" instead of pretending they are zero.
    """

    bill_number: str
    hospital_name: str
    bill_date: str
    total_minor_units: int
    patient_payable_minor_units: int
    comparison_status: str
    comparison_message: str
    insurance_covered_minor_units: int | None = None
    amount_paid_minor_units: int | None = None
    outstanding_balance_minor_units: int | None = None


def render_amount(minor_units: int) -> str:
    """Trusted amount in the canonical ``Rs 12345.00`` shape used everywhere."""

    return f"Rs {format_minor_units(minor_units)}"


def recorded_amounts(facts: ExplanationFacts) -> tuple[int, ...]:
    """Every recorded amount in minor units (the validator's allow-list)."""

    values = (
        facts.total_minor_units,
        facts.patient_payable_minor_units,
        facts.insurance_covered_minor_units,
        facts.amount_paid_minor_units,
        facts.outstanding_balance_minor_units,
    )
    return tuple(value for value in values if value is not None)


def recorded_dates(facts: ExplanationFacts) -> tuple[str, ...]:
    """Every recorded date (only the bill date exists today)."""

    return (facts.bill_date,) if facts.bill_date else ()


def build_trusted_facts(
    service: VerificationService,
    identification,
    comparison,
) -> tuple[TrustedBillFactsOut, ExplanationFacts]:
    """Authoritative facts for one verified identification, read server-side.

    Raises :class:`IdentificationNotVerifiableError` (fail closed) when the
    registry no longer resolves the identification's bill.
    """

    bill = service.bill_for_identification(identification)

    uploaded_amounts = None
    if comparison and comparison.status != COMPARISON_NO_UPLOADED_IMAGE:
        extracted = identification.extracted or {}
        uploaded_amounts = [
            UploadedAmountOut(
                label=item["label"], value=format_minor_units(int(item["minor_units"]))
            )
            for item in extracted.get("labelled_amounts", [])
            if isinstance(item, dict) and "minor_units" in item
        ]

    facts_out = TrustedBillFactsOut(
        bill_number=bill.bill_number,
        hospital_name=identification.hospital_name or "",
        bill_date=bill.bill_date,
        amounts={
            "total": TrustedAmountOut(
                label="total",
                value=format_minor_units(bill.total_amount_cents),
                authoritative=True,
            ),
            "patient_payable": TrustedAmountOut(
                label="patient_payable",
                value=format_minor_units(bill.patient_payable_cents),
                authoritative=True,
            ),
        },
        comparison=(
            ComparisonSummary(status=comparison.status, message=comparison.message)
            if comparison
            else None
        ),
        uploaded_amounts=uploaded_amounts,
    )
    model_facts = ExplanationFacts(
        bill_number=bill.bill_number,
        hospital_name=identification.hospital_name or "",
        bill_date=bill.bill_date,
        total_minor_units=bill.total_amount_cents,
        patient_payable_minor_units=bill.patient_payable_cents,
        comparison_status=comparison.status if comparison else COMPARISON_NO_UPLOADED_IMAGE,
        comparison_message=comparison.message if comparison else "",
    )
    return facts_out, model_facts


def facts_summary_lines(facts: ExplanationFacts) -> list[str]:
    """The minimal prompt block shared by every feature.

    Excludes patient identifiers, contact details, access codes, session ids
    and anything not necessary to explain the bill.
    """

    lines = [
        f"Hospital: {facts.hospital_name}",
        f"Bill number: {facts.bill_number}",
        f"Bill date: {facts.bill_date}",
        f"Total amount on record: {render_amount(facts.total_minor_units)}",
        (
            "Amount payable by patient on record: "
            f"{render_amount(facts.patient_payable_minor_units)}"
        ),
        f"Uploaded-amount comparison status: {facts.comparison_status}",
    ]
    if facts.comparison_message:
        lines.append(f"Comparison note (authoritative): {facts.comparison_message}")
    for label, value in (
        ("Insurance-covered amount", facts.insurance_covered_minor_units),
        ("Amount already paid", facts.amount_paid_minor_units),
        ("Outstanding balance", facts.outstanding_balance_minor_units),
    ):
        lines.append(
            f"{label} on record: {render_amount(value)}"
            if value is not None
            else f"{label} on record: not recorded"
        )
    return lines
