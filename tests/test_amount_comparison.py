"""Amount-comparison tests (parsing, labelling, comparison outcomes).

Unit-level tests cover the arithmetic and parsing rules; integration tests
drive a full upload → verify → compare flow through the API with mocked OCR
(a mock adapter, no Tesseract dependency).
"""

from __future__ import annotations

import pytest

from app.services.amount_comparison import (
    COMPARISON_AMOUNTS_DIFFER,
    COMPARISON_INSUFFICIENT_EVIDENCE,
    COMPARISON_MATCHED,
    COMPARISON_NO_UPLOADED_IMAGE,
    AmbiguousAmountError,
    compare_uploaded_amounts,
    extract_labelled_amounts,
    format_minor_units,
    parse_minor_units,
)
from app.services.records import BILLS, BillRecord


def bill(bill_number: str = "SUN-2026-004512") -> BillRecord:
    normalised = bill_number.replace("-", "")
    return next(b for b in BILLS if b.bill_number.replace("-", "") == normalised)


# --- Exact parsing -----------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12,480.00", 1_248_000),
        ("6240.00", 624_000),
        ("6240", 624_000),
        ("0.01", 1),
        ("594,000.00", 59_400_000),
        ("1,234,567.89", 123_456_789),
        ("63,150.75", 6_315_075),
        ("99999999999.99", 9_999_999_999_999),
    ],
)
def test_amounts_parse_into_exact_integer_minor_units(raw, expected) -> None:
    assert parse_minor_units(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "  ",
        "12,34.00",  # two-digit group: ambiguous, rejected
        "1,2",  # two-digit group: ambiguous, rejected
        "1,234,56",  # two-digit group
        "12.345",  # three decimals: not a minor-unit value
        "12,34,",  # trailing comma
        ",234",
        "1.2.3",
        "12,480,00",  # dot as decimal separator with two-digit frac: rejected
        "abc",
        "-5",
        "12 480.00",
    ],
)
def test_ambiguous_numerical_formats_are_rejected(raw) -> None:
    with pytest.raises(AmbiguousAmountError):
        parse_minor_units(raw)


def test_format_minor_units_is_exact_decimal_rendering() -> None:
    assert format_minor_units(1_248_000) == "12480.00"
    assert format_minor_units(624_000) == "6240.00"
    assert format_minor_units(1) == "0.01"


# --- Labelled extraction -----------------------------------------------------


def test_total_and_payable_labels_are_mapped() -> None:
    text = (
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Date of Issue: 14/03/2026 Total Amount: Rs. 12,480.00 "
        "Amount Payable: 6,240.00"
    )

    labelled = extract_labelled_amounts(text)

    assert [(a.label, a.minor_units) for a in labelled] == [
        ("total", 1_248_000),
        ("patient_payable", 624_000),
    ]


def test_grand_total_and_variant_labels_map_correctly() -> None:
    for text in (
        "Grand Total: 12,480.00",
        "Bill total 12480.00",
        "TOTAL: Rs 12,480.00",
    ):
        assert [(a.label, a.minor_units) for a in extract_labelled_amounts(text)] == [
            ("total", 1_248_000)
        ], text
    for text in (
        "Amount due: 6,240.00",
        "Patient payable 6240.00",
        "Balance Due: Rs. 6,240.00",
    ):
        assert [(a.label, a.minor_units) for a in extract_labelled_amounts(text)] == [
            ("patient_payable", 624_000)
        ], text


def test_unlabelled_monetary_values_are_never_comparable() -> None:
    text = "Amounts: Rs. 12,480.00 INR 500 Paid 100.00"

    labelled = extract_labelled_amounts(text)

    assert labelled == []


def test_ambiguous_labelled_values_are_dropped_not_guessed() -> None:
    text = "Total: Rs. 12,34.00"

    assert extract_labelled_amounts(text) == []


# --- Comparison outcomes ------------------------------------------------------


def test_matching_total_amount() -> None:
    result = compare_uploaded_amounts(
        bill(), extract_labelled_amounts("Total: 12,480.00"), uploaded=True
    )

    assert result.status == COMPARISON_MATCHED


def test_matching_patient_payable_amount() -> None:
    result = compare_uploaded_amounts(
        bill(), extract_labelled_amounts("Amount payable: 6,240.00"), uploaded=True
    )

    assert result.status == COMPARISON_MATCHED


def test_matching_labelled_amounts_together() -> None:
    labelled = extract_labelled_amounts("Total Amount: 12,480.00 Amount Payable: 6,240.00")

    result = compare_uploaded_amounts(bill(), labelled, uploaded=True)

    assert result.status == COMPARISON_MATCHED


def test_differing_total_amount() -> None:
    result = compare_uploaded_amounts(
        bill(), extract_labelled_amounts("Total: 13,000.00"), uploaded=True
    )

    assert result.status == COMPARISON_AMOUNTS_DIFFER
    assert "differ" in result.message.lower()


def test_differing_patient_payable_amount() -> None:
    result = compare_uploaded_amounts(
        bill(), extract_labelled_amounts("Amount payable: 7,999.00"), uploaded=True
    )

    assert result.status == COMPARISON_AMOUNTS_DIFFER


def test_unlabelled_values_yield_insufficient_evidence() -> None:
    """Only unlabelled numbers present: nothing reliably comparable."""

    result = compare_uploaded_amounts(
        bill(), extract_labelled_amounts("Paid Rs. 12,480.00"), uploaded=True
    )

    assert result.status == COMPARISON_INSUFFICIENT_EVIDENCE


def test_missing_extracted_amounts_with_upload() -> None:
    """OCR ran (uploaded=True) but extracted no labelled amounts."""

    result = compare_uploaded_amounts(bill(), [], uploaded=True)

    assert result.status == COMPARISON_INSUFFICIENT_EVIDENCE


def test_no_uploaded_image_means_no_comparison() -> None:
    result = compare_uploaded_amounts(bill(), [], uploaded=False)

    assert result.status == COMPARISON_NO_UPLOADED_IMAGE


def test_conflicting_labels_prevent_a_claim() -> None:
    """Two contradictory readings of the same label: never claim match/differ."""

    from app.services.amount_comparison import LabelledAmount

    result = compare_uploaded_amounts(
        bill(),
        [
            LabelledAmount(label="total", raw="12,480.00", minor_units=1_248_000),
            LabelledAmount(label="total", raw="13,000.00", minor_units=1_300_000),
        ],
        uploaded=True,
    )

    assert result.status == COMPARISON_INSUFFICIENT_EVIDENCE


def test_dates_and_bill_number_text_read_as_no_amounts() -> None:
    """OCR text with dates/bill numbers but no monetary values."""

    result = compare_uploaded_amounts(
        bill(),
        extract_labelled_amounts(
            "Bill Number: SUN-2026-004512 Date of issue: 14/03/2026"
        ),
        uploaded=True,
    )

    assert result.status == COMPARISON_INSUFFICIENT_EVIDENCE


def test_large_values_do_not_lose_precision() -> None:
    huge = BillRecord(
        bill_id="bill-x",
        bill_number="X-2026-000001",
        hospital_id="hosp-sunrise",
        bill_date="2026-01-01",
        total_amount_cents=9_999_999_999_999,
        patient_payable_cents=9_999_999_999_998,
    )

    total_only = extract_labelled_amounts("Total: 99,999,999,999.99")
    # 99,999,999,999.99 rupees == 9_999_999_999_999 hundredths: exact.
    assert total_only[0].minor_units == 9_999_999_999_999
    result = compare_uploaded_amounts(huge, total_only, uploaded=True)
    assert result.status == COMPARISON_MATCHED

    # A one-hundredth difference is detected exactly (no float rounding).
    result = compare_uploaded_amounts(
        huge,
        extract_labelled_amounts(
            "Total: 99,999,999,999.99 Amount payable: 99,999,999,999.97"
        ),
        uploaded=True,
    )
    assert result.status == COMPARISON_AMOUNTS_DIFFER
    # And an exact pair matches too.
    result = compare_uploaded_amounts(
        huge,
        extract_labelled_amounts(
            "Total: 99,999,999,999.99 Amount payable: 99,999,999,999.98"
        ),
        uploaded=True,
    )
    assert result.status == COMPARISON_MATCHED


# --- End-to-end amount flows (mocked OCR, real API) --------------------------


class FakeOcrAdapter:
    engine = "fake"

    def __init__(self, text: str, mean_confidence: float = 95.0) -> None:
        self.text = text
        self.mean_confidence = mean_confidence

    def extract_image_text(self, image):
        from app.services.ocr import OcrResult

        return OcrResult(text=self.text, mean_confidence=self.mean_confidence)


def _png_bytes() -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), color=(240, 240, 240)).save(buffer, format="PNG")
    return buffer.getvalue()


async def _upload_bill(client, app, session_id: str, ocr_text: str) -> dict:
    app.state.ocr_adapter = FakeOcrAdapter(ocr_text)
    response = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": ("bill.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _verify(client, session_id: str, identification_id: str, code: str = "DEMO1234"):
    return await client.post(
        f"/api/v1/identifications/{identification_id}/verify",
        json={"session_id": session_id, "access_code": code},
    )


async def _protected(client, session_id: str, identification_id: str):
    return await client.get(
        f"/api/v1/verified-bills/{identification_id}", headers={"X-Session-ID": session_id}
    )


async def test_upload_with_matching_labelled_amounts_verifies_and_matches(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    from tests.conftest import create_consented_session

    session_id = await create_consented_session(client)
    body = await _upload_bill(
        client,
        app,
        session_id,
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Total Amount: Rs. 12,480.00 Amount Payable: 6,240.00",
    )

    verified = await _verify(client, session_id, body["identification_id"])
    assert verified.status_code == 200
    assert verified.json()["comparison"]["status"] == COMPARISON_MATCHED

    protected = await _protected(client, session_id, body["identification_id"])
    assert protected.status_code == 200
    payload = protected.json()
    assert payload["amounts"]["total_amount"]["value"] == "12480.00"
    assert payload["amounts"]["patient_payable"]["value"] == "6240.00"
    assert payload["comparison"]["status"] == COMPARISON_MATCHED
    assert payload["uploaded_amounts"] == [
        {"label": "total", "value": "12480.00", "authoritative": False},
        {"label": "patient_payable", "value": "6240.00", "authoritative": False},
    ]


async def test_upload_with_differing_labelled_total_verifies_but_flags_mismatch(
    client, app, verification_factory
) -> None:
    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    from tests.conftest import create_consented_session

    session_id = await create_consented_session(client)
    body = await _upload_bill(
        client,
        app,
        session_id,
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 "
        "Total Amount: Rs. 13,000.00 Amount Payable: Rs. 6,500.00",
    )

    verified = await _verify(client, session_id, body["identification_id"])
    assert verified.status_code == 200
    assert verified.json()["comparison"]["status"] == COMPARISON_AMOUNTS_DIFFER

    protected = await _protected(client, session_id, body["identification_id"])
    payload = protected.json()
    mismatch = payload["comparison"]["status"] == COMPARISON_AMOUNTS_DIFFER
    assert mismatch, payload

    # The record keeps its authoritative values; uploads are flagged separately.
    assert payload["amounts"]["total_amount"]["value"] == "12480.00"
    assert payload["uploaded_amounts"] == [
        {"label": "total", "value": "13000.00", "authoritative": False},
        {"label": "patient_payable", "value": "6500.00", "authoritative": False},
    ]
    assert mismatch and "human support" in payload["comparison"]["message"].lower()


async def test_upload_without_reliably_comparable_amounts_verifies_anyway(
    client, app, verification_factory
) -> None:
    """A valid code with unreadable/absent amounts still verifies."""

    verification_factory(codes={"bill-sun-004512": "DEMO1234"})
    from tests.conftest import create_consented_session

    session_id = await create_consented_session(client)
    body = await _upload_bill(
        client,
        app,
        session_id,
        "SUNRISE MULTISPECIALITY HOSPITAL Bill Number: SUN-2026-004512 (blurry totals)",
    )

    verified = await _verify(client, session_id, body["identification_id"])
    assert verified.status_code == 200
    assert verified.json()["comparison"] is not None
    assert verified.json()["comparison"]["status"] == COMPARISON_INSUFFICIENT_EVIDENCE

    protected = await _protected(client, session_id, body["identification_id"])
    assert protected.status_code == 200
    assert protected.json()["uploaded_amounts"] == []
