"""Unit tests for the Tesseract OCR adapter contract.

Tests monkeypatch ``pytesseract`` so the suite never depends on a local OCR
executable; the executable's absence is itself covered by the
unavailable-mapping test.
"""

from __future__ import annotations

import pytest
from PIL import Image

from app.core.errors import OcrProcessingError, OcrUnavailableError
from app.services import ocr as ocr_module
from app.services.ocr import TesseractOcrAdapter, build_ocr_adapter


@pytest.fixture
def small_image() -> Image.Image:
    return Image.new("RGB", (40, 30), color=(255, 255, 255))


@pytest.fixture
def fake_pytesseract(monkeypatch):
    """Install a stub module in place of pytesseract."""

    import sys
    import types

    module = types.ModuleType("pytesseract")
    module.Output = types.SimpleNamespace(DICT="dict")

    class TesseractNotFoundError(EnvironmentError):
        pass

    module.TesseractNotFoundError = TesseractNotFoundError

    # Real shape of a tesseract image_to_data dict for one word.
    doc_dict = {
        "text": ["Sunrise", "Hospital", "", "Bill"],
        "conf": [92.0, 88.5, -1.0, 75.0],
    }

    def image_to_data(image, lang="eng", output_type=None):
        return doc_dict

    module.image_to_data = image_to_data
    inner = types.ModuleType("pytesseract.pytesseract")
    inner.tesseract_cmd = "tesseract"
    module.pytesseract = inner
    monkeypatch.setitem(sys.modules, "pytesseract", module)
    return module


async def test_adapter_maps_missing_executable_to_unavailable(
    fake_pytesseract, monkeypatch, small_image
) -> None:
    import pytesseract

    def no_engine(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(fake_pytesseract, "image_to_data", no_engine)

    adapter = TesseractOcrAdapter()

    with pytest.raises(OcrUnavailableError):
        adapter.extract_image_text(small_image)


async def test_adapter_maps_processing_crash_to_processing_error(
    fake_pytesseract, monkeypatch, small_image
) -> None:
    def crash(*args, **kwargs):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(fake_pytesseract, "image_to_data", crash)

    adapter = TesseractOcrAdapter()

    with pytest.raises(OcrProcessingError):
        adapter.extract_image_text(small_image)


async def test_adapter_returns_text_and_mean_confidence(fake_pytesseract, small_image) -> None:
    adapter = TesseractOcrAdapter()
    result = adapter.extract_image_text(small_image)

    assert result.text == "Sunrise Hospital Bill"
    # The adapter reports mean confidence rounded to two decimals.
    assert result.mean_confidence == pytest.approx(85.17)


async def test_configured_tesseract_cmd_is_handed_to_pytesseract(
    fake_pytesseract, small_image
) -> None:
    adapter = TesseractOcrAdapter(tesseract_cmd=r"C:/Program Files/Tesseract-OCR/tesseract.exe")

    adapter.extract_image_text(small_image)

    # The cmd is set on the inner pytesseract module that pytesseract.py uses.
    assert (
        fake_pytesseract.pytesseract.tesseract_cmd
        == r"C:/Program Files/Tesseract-OCR/tesseract.exe"
    )


def test_build_falls_back_to_well_known_install_location(monkeypatch) -> None:
    class Settings:
        ocr_engine = "tesseract"
        ocr_language = "eng"
        ocr_tesseract_cmd = ""

    monkeypatch.setattr(
        ocr_module, "_WELL_KNOWN_TESSERACT", (ocr_module.Path("C:/definitely/not/real.exe"),)
    )

    adapter = build_ocr_adapter(Settings())

    assert adapter.tesseract_cmd == ""


def test_build_prefers_explicit_setting_and_skips_probes(monkeypatch, tmp_path) -> None:
    class Settings:
        ocr_engine = "tesseract"
        ocr_language = "eng"
        ocr_tesseract_cmd = str(tmp_path / "custom-tesseract.exe")

    probed: list[bool] = []
    original = ocr_module._WELL_KNOWN_TESSERACT
    monkeypatch.setattr(
        ocr_module,
        "_WELL_KNOWN_TESSERACT",
        tuple(path for path in original if not probed.append(True) or False),
    )

    adapter = build_ocr_adapter(Settings())

    assert adapter.tesseract_cmd == str(tmp_path / "custom-tesseract.exe")
