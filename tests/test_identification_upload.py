"""Tests for ``POST /api/v1/identifications/upload`` with a mocked OCR adapter.

The real Tesseract engine is never required here — OCR is mocked for success
paths, and its unavailability/failure behaviour is asserted through the adapter
contract, which the route consumes.
"""

from __future__ import annotations

import io

from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image

from app.core.config import Settings
from app.core.errors import OcrProcessingError, OcrUnavailableError
from app.main import create_application
from app.services.ocr import OcrResult
from app.services.records import HospitalRecord, InMemoryBillRecordAccess

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

GOOD_OCR_TEXT = (
    "SUNRISE MULTISpeciality HOSPITAL\n"
    "Bill Number : SUN-2026-004512\n"
    "Date of Issue: 14/03/2026\n"
    "Total Amount: Rs. 12,480.00\n"
    "Amount Payable: 6,240.00"
)

SAFE_RESPONSE_KEYS = {
    "identification_id",
    "status",
    "hospital_name",
    "bill_number",
    "message",
    "next_action",
}


class FakeOcrAdapter:
    """Deterministic stand-in satisfying the OcrAdapter protocol."""

    engine = "fake"

    def __init__(
        self,
        text: str = GOOD_OCR_TEXT,
        mean_confidence: float | None = 95.0,
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.mean_confidence = mean_confidence
        self.error = error
        self.seen_images: list[Image.Image] = []

    def extract_image_text(self, image: Image.Image) -> OcrResult:
        if self.error is not None:
            raise self.error
        self.seen_images.append(image)
        return OcrResult(text=self.text, mean_confidence=self.mean_confidence)


def _jpeg_bytes(width: int = 60, height: int = 40) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(250, 250, 250)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes(width: int = 60, height: int = 40, color=(240, 240, 240)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _webp_bytes(width: int = 60, height: int = 40) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(245, 245, 245)).save(buffer, format="WebP")
    return buffer.getvalue()


def _app(ocr: FakeOcrAdapter | None = None, **setting_overrides: object) -> FastAPI:
    settings = Settings(
        _env_file=None,
        environment="test",
        cors_origins="http://localhost:3000",
        log_level="WARNING",
        **setting_overrides,
    )
    application = create_application(settings)
    if ocr is not None:
        application.state.ocr_adapter = ocr
    return application


async def _granted_session(client: AsyncClient, app: FastAPI) -> str:
    response = await client.post("/api/v1/sessions")
    session_id = response.json()["session_id"]
    await client.post(
        f"/api/v1/sessions/{session_id}/consent",
        json={
            "decision": "granted",
            "policy_version": app.state.settings.consent_policy_version,
        },
    )
    return session_id


async def _upload_with_session(
    client: AsyncClient,
    app: FastAPI,
    data: bytes,
    *,
    name: str = "bill.png",
    content_type: str = "image/png",
) -> tuple:
    """Create a consented session, post the upload and return (session_id, response)."""

    session_id = await _granted_session(client, app)
    response = await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": session_id},
        files={"file": (name, data, content_type)},
    )
    return session_id, response


async def _upload_for_bare(client: AsyncClient, data: bytes) -> object:
    bare = await client.post("/api/v1/sessions")
    return await client.post(
        "/api/v1/identifications/upload",
        data={"session_id": bare.json()["session_id"]},
        files={"file": ("bill.png", data, "image/png")},
    )


async def test_consent_is_required_before_upload(client_factory) -> None:
    app = _app()
    async with client_factory(app) as client:
        response = await _upload_for_bare(client, _png_bytes())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "consent_required"


async def test_unknown_session_is_rejected_for_upload(client_factory) -> None:
    app = _app()
    async with client_factory(app) as client:
        response = await client.post(
            "/api/v1/identifications/upload",
            data={"session_id": "unknown-session-identifier-0123"},
            files={"file": ("bill.png", _png_bytes(), "image/png")},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"


async def test_jpeg_upload_with_clean_ocr_text_identifies_the_bill(client_factory) -> None:
    adapter = FakeOcrAdapter()
    app = _app(ocr=adapter)
    async with client_factory(app) as client:
        session_id, response = await _upload_with_session(
            client, app, _jpeg_bytes(), name="bill.jpg", content_type="image/jpeg"
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == SAFE_RESPONSE_KEYS
    assert body["status"] == "access_code_required"
    assert body["hospital_name"] == "Sunrise Multispeciality Hospital"
    assert body["bill_number"] == "SUN-2026-004512"
    assert body["next_action"] == "verify_access_code"
    # The decoded image reached the adapter at its validated dimensions...
    assert adapter.seen_images[0].size == (60, 40)
    # ...and monetary candidates stayed strictly on the server.
    session = app.state.session_store.get(session_id)
    assert session.identifications[0].extracted["amounts"] == ["12,480.00", "6,240.00"]
    assert "12,480" not in response.text
    assert "6,240" not in response.text


async def test_webp_upload_is_accepted(client_factory) -> None:
    app = _app(ocr=FakeOcrAdapter())
    async with client_factory(app) as client:
        _, response = await _upload_with_session(
            client, app, _webp_bytes(), name="bill.webp", content_type="image/webp"
        )

    assert response.status_code == 200
    assert response.json()["status"] == "access_code_required"


async def test_client_content_type_is_ignored(client_factory) -> None:
    """A PNG payload mislabelled as text/plain still identifies."""

    app = _app(ocr=FakeOcrAdapter())
    async with client_factory(app) as client:
        _, response = await _upload_with_session(
            client, app, _png_bytes(), name="bill.txt", content_type="text/plain"
        )

    assert response.status_code == 200
    assert response.json()["status"] == "access_code_required"


async def test_empty_ocr_text_yields_unreadable_image(client_factory) -> None:
    app = _app(ocr=FakeOcrAdapter(text="", mean_confidence=None))
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unreadable_image"
    assert body["next_action"] == "enter_bill_number_manually"
    assert "manually" in body["message"]
    assert body["hospital_name"] is None
    assert body["bill_number"] is None


async def test_low_confidence_ocr_is_treated_as_unreadable(client_factory) -> None:
    app = _app(ocr=FakeOcrAdapter(mean_confidence=20.0))
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unreadable_image"
    assert body["next_action"] == "enter_bill_number_manually"


async def test_missing_bill_number_is_reported_with_hospital(client_factory) -> None:
    readable_but_no_bill = "Sunrise Multispeciality Hospital\nTotal Amount: Rs. 100.00"
    app = _app(ocr=FakeOcrAdapter(text=readable_but_no_bill))
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "bill_number_not_found"
    assert body["hospital_name"] == "Sunrise Multispeciality Hospital"
    assert body["bill_number"] is None
    assert body["next_action"] == "enter_bill_number_manually"
    # financial candidates are never echoed
    assert "100" not in body["message"]


async def test_multiple_hospitals_in_text_become_ambiguous(client_factory) -> None:
    hospital_a = HospitalRecord("hosp-city-a", "City Care Hospital", "CITY-A", ())
    hospital_b = HospitalRecord("hosp-city-b", "Care Point Clinic", "CAREP", ())
    app = _app(ocr=FakeOcrAdapter(text="City Care Hospital and Care Point Clinic"))
    app.state.records = InMemoryBillRecordAccess(hospitals=(hospital_a, hospital_b), bills=())
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ambiguous_hospital"
    assert body["next_action"] == "provide_hospital_identifier"


async def test_unsupported_file_format_is_rejected(client_factory) -> None:
    app = _app()
    async with client_factory(app) as client:
        _, response = await _upload_with_session(
            client, app, b"GIF89a" + b"junk-image-data", name="animated.gif"
        )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "unsupported_image_format"
    assert "JPEG, PNG and WebP" in error["message"]


async def test_oversized_upload_is_rejected_without_decoding(client_factory) -> None:
    app = _app(bill_upload_max_size_mb=1)
    oversized = PNG_MAGIC + b"0" * (1024 * 1024 + 1024)
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, oversized)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_corrupt_image_is_rejected(client_factory) -> None:
    app = _app()
    async with client_factory(app) as client:
        _, response = await _upload_with_session(
            client, app, PNG_MAGIC + b"\x00\x01corrupt-not-a-real-png"
        )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "corrupt_image"
    assert "manually" in error["message"]


async def test_image_dimensions_above_limit_are_rejected(client_factory) -> None:
    # The smallest allowed configured limit is 100px, so exceed that.
    app = _app(image_max_dimension_px=100)
    big = _png_bytes(width=140, height=120)
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, big)

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "image_dimensions_exceed_limit"
    assert "140x120" in error["message"]


async def test_ocr_engine_unavailable_is_a_technical_error(client_factory) -> None:
    app = _app(ocr=FakeOcrAdapter(error=OcrUnavailableError()))
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 503
    error = response.json()["error"]
    # The failure must not be disguised as a business outcome.
    assert error["code"] == "ocr_unavailable"
    assert "unavailable" in error["message"]
    assert "Manual bill-number entry" in error["message"]


async def test_ocr_processing_failure_is_a_technical_error(client_factory) -> None:
    app = _app(ocr=FakeOcrAdapter(error=OcrProcessingError()))
    async with client_factory(app) as client:
        _, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "ocr_processing_failed"
    assert set(error) == {"code", "message", "request_id", "details"}


async def test_uploaded_images_are_not_persisted_anywhere(client_factory) -> None:
    """Detection, not storage: nothing about the image survives the request."""

    app = _app(ocr=FakeOcrAdapter())
    async with client_factory(app) as client:
        session_id, response = await _upload_with_session(client, app, _png_bytes())

    assert response.status_code == 200
    record = app.state.session_store.get(session_id).identifications[0]
    futures = {key: value for key, value in record.extracted.items() if value}
    # Text candidates only — never the decoded image or any of its bytes.
    assert set(futures) <= {"bill_date_raw", "amounts", "labelled_amounts"}
    assert "text" not in record.extracted
