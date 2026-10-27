"""Unit tests for the shared GenAI output validator (Phase 8 + Phase 9).

The validator is the last line of defence for every generated text, so its
formatting tolerance and its rejections are tested directly, without a model.
"""

from __future__ import annotations

from app.services.ai_validation import (
    UNSUPPORTED_CLAIM_PATTERNS,
    allowed_amount_values,
    allowed_date_forms,
    amount_problems,
    date_problems,
    label_amount_problems,
    length_problems,
    money_candidates,
    phrase_problems,
    script_problems,
    validate_generated,
)

#: The Sunrise record: Rs 12480.00 total, Rs 6240.00 patient-payable.
ALLOWED = allowed_amount_values([1_248_000, 624_000])
DATES = allowed_date_forms(["2026-03-14"])


# --- Amounts ---------------------------------------------------------------------


def test_currency_marked_amounts_match_the_record() -> None:
    assert amount_problems("The recorded total is Rs 12480.00.", ALLOWED) == []
    assert amount_problems("Your share is ₹6,240.00 today.", ALLOWED) == []
    assert amount_problems("Recorded total: INR 12,480", ALLOWED) == []


def test_currency_marked_unknown_amount_is_rejected() -> None:
    problems = amount_problems("The recorded total is Rs 9999.00.", ALLOWED)

    assert problems == ["unsupported_amount:9999.00"]


def test_bare_two_decimal_amounts_are_validated() -> None:
    # Sentence periods are not mistaken for decimals, and a stray figure is
    # still caught even without a currency marker.
    assert amount_problems("The total is 12480.00.", ALLOWED) == []
    assert amount_problems("Your share is 6240.00 rupees.", ALLOWED) == []
    assert amount_problems("The total is 999.99.", ALLOWED) == ["unsupported_amount:999.99"]


def test_over_precise_amounts_are_rejected_not_rounded() -> None:
    # 12480.005 must not be truncated to the recorded 12480.00.
    assert amount_problems("The total is Rs 12480.005.", ALLOWED) == [
        "unsupported_amount_precision:12480.005"
    ]
    assert amount_problems("The total is 12480.005.", ALLOWED) == [
        "unsupported_amount_precision:12480.005"
    ]
    # A genuine one/two-decimal rendering of the record is still accepted.
    assert amount_problems("The total is Rs 12480.0.", ALLOWED) == []


def test_amounts_attached_to_the_wrong_label_are_rejected() -> None:
    assert label_amount_problems(
        "The total bill amount is Rs 6240.00.",
        total_minor_units=1_248_000,
        patient_payable_minor_units=624_000,
    ) == ["mislabelled_amount:total:6240.00"]
    assert label_amount_problems(
        "The patient payable amount is Rs 12480.00.",
        total_minor_units=1_248_000,
        patient_payable_minor_units=624_000,
    ) == ["mislabelled_amount:patient_payable:12480.00"]
    assert (
        label_amount_problems(
            "The total is Rs 12480.00 and your share is Rs 6240.00.",
            total_minor_units=1_248_000,
            patient_payable_minor_units=624_000,
        )
        == []
    )


def test_bare_integer_after_a_label_is_validated() -> None:
    assert label_amount_problems(
        "The total is 9999.",
        total_minor_units=1_248_000,
        patient_payable_minor_units=624_000,
    ) == ["unsupported_amount:9999"]


def test_bare_integers_are_not_treated_as_money() -> None:
    assert money_candidates("It has 3 sentences and 5 items in 2026.") == []


def test_dates_are_masked_before_bare_amounts_are_read() -> None:
    assert money_candidates("Bill dated 14.03.2026 and issued on 2026-03-14.") == []


def test_indian_grouping_and_localised_digits() -> None:
    indian = allowed_amount_values([12_480_000])
    assert amount_problems("Rs 1,24,800.00", indian) == []
    assert amount_problems("₹ १२४८०.००", ALLOWED) == []  # noqa: RUF001 - digits are the test
    assert amount_problems("₹ ९९९.००", ALLOWED) == ["unsupported_amount:999.00"]  # noqa: RUF001
    assert amount_problems("₹ ೧೨೪೮೦.೦೦", ALLOWED) == []  # noqa: RUF001 - Kannada digits


# --- Dates -----------------------------------------------------------------------


def test_recorded_dates_accept_approved_renderings() -> None:
    assert date_problems("Bill dated 2026-03-14.", DATES) == []
    assert date_problems("Bill dated 14.03.2026.", DATES) == []
    assert date_problems("Bill dated 14/03/2026.", DATES) == []


def test_unrecorded_dates_are_rejected() -> None:
    assert date_problems("Bill dated 15.03.2026.", DATES) == ["unsupported_date:15.03.2026"]
    assert date_problems("Bill dated 2026-03-15.", DATES) == ["unsupported_date:2026-03-15"]


# --- Claims, length and script ----------------------------------------------------


def test_payment_status_claims_are_rejected() -> None:
    problems = phrase_problems("This bill has been paid and payment received.")

    assert problems
    assert all(problem.startswith("forbidden_claim:") for problem in problems)


def test_other_unsupported_claims_are_rejected() -> None:
    for text in (
        "Insurance will cover the rest.",
        "This is an overcharged bill.",
        "This is an over-charged bill.",
        "You must pay before the deadline.",
        "We guarantee approval.",
        "Your insurance has approved the claim.",
    ):
        assert phrase_problems(text), text


def test_length_is_bounded_not_truncated() -> None:
    assert length_problems("short", 10) == []
    assert length_problems("x" * 11, 10) == ["output_too_long:11"]


def test_language_script_is_enforced() -> None:
    assert script_problems("This is English.", "en") == []
    assert script_problems("This is English.", "hi") == ["language_mismatch:hi"]
    assert script_problems("यह हिंदी है।", "hi") == []
    assert script_problems("ಇದು ಕನ್ನಡ.", "kn") == []
    assert script_problems("यह हिंदी है।", "kn") == ["language_mismatch:kn"]


# --- Aggregation -----------------------------------------------------------------


def test_validate_generated_combines_every_check() -> None:
    problems = validate_generated(
        "Bill 2026-03-15 has been paid: Rs 9999.00. " + "padding " * 50,
        language="en",
        allowed_minor_units=[1_248_000, 624_000],
        allowed_iso_dates=["2026-03-14"],
        forbidden_patterns=UNSUPPORTED_CLAIM_PATTERNS,
        max_chars=100,
    )

    assert any(problem.startswith("output_too_long") for problem in problems)
    assert any(problem.startswith("forbidden_claim:") for problem in problems)
    assert "unsupported_amount:9999.00" in problems
    assert "unsupported_date:2026-03-15" in problems


def test_validate_generated_accepts_a_clean_answer() -> None:
    assert (
        validate_generated(
            "Your bill dated 14.03.2026 has a recorded total of Rs 12480.00.",
            language="en",
            allowed_minor_units=[1_248_000, 624_000],
            allowed_iso_dates=["2026-03-14"],
            forbidden_patterns=UNSUPPORTED_CLAIM_PATTERNS,
            max_chars=200,
        )
        == []
    )
