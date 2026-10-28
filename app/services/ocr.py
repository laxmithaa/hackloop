"""Local, non-generative OCR adapter.

Phase 2 uses Tesseract through ``pytesseract``. The engine is an external
executable; see the README for its one-time installation. The adapter converts
a decoded image into an :class:`OcrResult` holding raw text and an optional mean
word confidence. Nothing here interprets instructions found in the image, and
no generative model is involved.

The adapter is deliberately lazy with imports so the API can still run — and
report a precise 503 — when pytesseract or the Tesseract executable is missing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.errors import OcrProcessingError, OcrUnavailableError

logger = logging.getLogger(__name__)

EngineName = str


@dataclass(frozen=True)
class OcrResult:
    """Raw output of one OCR pass. Unverified by definition."""

    text: str
    #: Mean Tesseract word confidence (0-100). ``None`` when no words were found.
    mean_confidence: float | None


class OcrAdapter(Protocol):
    """Anything that can turn a decoded image into raw OCR text."""

    engine: EngineName

    def extract_image_text(self, image) -> OcrResult:
        """Run OCR over a decoded Pillow ``Image``."""
        ...


class TesseractOcrAdapter:
    """pytesseract-backed adapter; the module's answer for ``HBN_OCR_ENGINE=tesseract``."""

    engine = "tesseract"

    def __init__(self, language: str = "eng", tesseract_cmd: str = "") -> None:
        self.language = language
        self.tesseract_cmd = tesseract_cmd

    def extract_image_text(self, image) -> OcrResult:
        try:
            import pytesseract
        except ImportError as exc:  # pragma: no cover - exercised via 503 path without install
            raise OcrUnavailableError(
                "The OCR library (pytesseract) is not installed on this server."
            ) from exc

        # An explicit executable location (settings) wins; pytesseract's own
        # PATH resolution stays the default otherwise. The cmd lives on the
        # inner module (``pytesseract.pytesseract``), not on the package alias.
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        try:
            data = pytesseract.image_to_data(
                image.convert("RGB"),
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractNotFoundError as exc:
            logger.warning("tesseract executable is not available")
            raise OcrUnavailableError() from exc
        except Exception as exc:
            logger.warning("tesseract raised an unexpected error", exc_info=True)
            raise OcrProcessingError() from exc

        words: list[str] = []
        confidences: list[float] = []
        for text, confidence in zip(data.get("text", []), data.get("conf", []), strict=False):
            stripped = (text or "").strip()
            # Tesseract marks non-word rows with -1 confidence; ignore those.
            if stripped and isinstance(confidence, (int, float)) and confidence >= 0:
                words.append(stripped)
                confidences.append(float(confidence))

        text = " ".join(words)
        mean_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None
        return OcrResult(text=text, mean_confidence=mean_confidence)


# Install locations used by the common Windows Tesseract distributions; probed
# only when HBN_OCR_TESSERACT_CMD is empty and the engine is not on PATH.
_WELL_KNOWN_TESSERACT = (
    Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
    Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
)


def build_ocr_adapter(settings) -> OcrAdapter:
    """Build the adapter configured in settings (only Tesseract exists in Phase 2)."""

    if settings.ocr_engine != "tesseract":  # pragma: no cover - Literal type guards this
        raise ValueError(f"Unsupported OCR engine: {settings.ocr_engine}")
    tesseract_cmd = settings.ocr_tesseract_cmd
    if not tesseract_cmd:
        for candidate in _WELL_KNOWN_TESSERACT:
            if candidate.is_file():
                tesseract_cmd = str(candidate)
                break
    return TesseractOcrAdapter(language=settings.ocr_language, tesseract_cmd=tesseract_cmd)
