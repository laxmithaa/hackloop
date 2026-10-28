"""Unit tests for identification logic: candidate extraction and registry matching."""

from __future__ import annotations

import pytest

from app.services.identification import (
    STATUS_ACCESS_CODE_REQUIRED,
    STATUS_BILL_NOT_FOUND,
    STATUS_UNREADABLE_IMAGE,
    extract_candidates,
    resolve_from_ocr,
)
from app.services.records import (
    InMemoryBillRecordAccess,
    match_key,
    normalise_bill_number,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SUN-2026-004512", "SUN2026004512"),
        ("sun. 2026 - 004512", "SUN2026004512"),
        ("  SUN 2026 004512 ", "SUN2026004512"),
    ],
)
def test_bill_normalisation_is_punctuation_and_spacing_agnostic(raw, expected):
    assert normalise_bill_number(raw) == expected


def test_match_key_ignores_case_and_punctuation():
    assert match_key("  Sunrise MultispeCIALITY hospital! ") == "sunrisemultispecialityhospital"


@pytest.mark.parametrize(
    "ocr_text",
    [
        "B i l l  N o . : S U N-2026-004512",  # not supported spacing inside label — no match
        "Invoice for services rendered",  # nothing at all
    ],
)
def test_no_bill_candidate_when_text_does_not_contain_one(ocr_text):
    assert extract_candidates(ocr_text).bill_number is None


@pytest.mark.parametrize(
    "ocr_text",
    [
        "Bill Number : SUN-2026-004512",
        "bill no: sun-2026-004512.",
        "BILL No. sundries 004512",
    ],
)
def test_labelled_bill_numbers_are_extracted(ocr_text):
    # The labelled pattern keeps what follows, normalisation then strips separators.
    candidates = extract_candidates(ocr_text)
    assert candidates.bill_number is not None
    assert candidates.bill_number.startswith("SUN")


def test_structural_fallback_extracts_printed_bill_number():
    candidates = extract_candidates("Hospital receipt GME-2026-001122 summary")
    assert candidates.bill_number == "GME2026001122"


def test_labelled_capture_ignores_words_following_the_bill_number():
    """Real Tesseract merges the label line with the next line into one string."""

    ocr_text = (
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Date of Issue: 14/03/2026 Total Amount: Rs. 12,480.00"
    )

    candidates = extract_candidates(ocr_text)

    assert candidates.bill_number == "SUN2026004512"
    assert candidates.bill_date_raw == "14/03/2026"
    assert candidates.amounts == ["12,480.00"]


def test_labelled_capture_without_structural_shape_still_extracts_after_trim():
    candidates = extract_candidates("Bill No: ABZ77/33 Total 500.00")

    assert candidates.bill_number == "ABZ7733"  # punctuation stripped, tail words gone


def test_dates_and_amounts_are_extracted_server_side_only():
    text = "Date of issue: 14/03/2026 Total: Rs. 12,480.00 INR 8,320.50 Payable: 6240.00"
    candidates = extract_candidates(text)

    assert candidates.bill_date_raw == "14/03/2026"
    assert candidates.amounts == ["12,480.00", "8,320.50", "6240.00"]


def test_registry_matches_hospital_name_variants():
    access = InMemoryBillRecordAccess()

    for text in (
        "sunrise multispeciality hospital!",
        "SUNRISE HOSPITAL",
        "receipt from  SUNRISE-HSP",
        "Greenmeadow city hospital ward 3",
    ):
        assert len(access.match_hospitals(text)) == 1, text

    assert access.match_hospitals("blinking star nursing home") == []


def test_resolve_from_ocr_requires_readable_bill_number():
    access = InMemoryBillRecordAccess()

    outcome = resolve_from_ocr(
        access,
        candidates=extract_candidates("Thank you for visiting Sunrise Hospital."),
        text_matched_hospitals=access.match_hospitals("Sunrise Hospital"),
        low_confidence=False,
        empty_text=False,
    )
    assert outcome.status == "bill_number_not_found"
    assert outcome.hospital is not None


def test_resolve_from_ocr_low_confidence_is_never_a_guess():
    outcome = resolve_from_ocr(
        InMemoryBillRecordAccess(),
        candidates=extract_candidates("Bill no: SUN-2026-004512"),
        text_matched_hospitals=[],
        low_confidence=True,
        empty_text=False,
    )
    assert outcome.status == STATUS_UNREADABLE_IMAGE


def test_resolve_from_ocr_finds_bill_without_hospital_hint():
    access = InMemoryBillRecordAccess()
    outcome = resolve_from_ocr(
        access,
        candidates=extract_candidates("Bill no: SUN-2026-004512."),
        text_matched_hospitals=[],
        low_confidence=False,
        empty_text=False,
    )
    assert outcome.status == STATUS_ACCESS_CODE_REQUIRED
    assert outcome.bill_number == "SUN-2026-004512"


def test_unknown_bill_number_is_bill_not_found():
    outcome = resolve_from_ocr(
        InMemoryBillRecordAccess(),
        candidates=extract_candidates("Bill no: ZZZ-2026-777777"),
        text_matched_hospitals=[],
        low_confidence=False,
        empty_text=False,
    )
    assert outcome.status == STATUS_BILL_NOT_FOUND
