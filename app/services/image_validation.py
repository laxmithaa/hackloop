"""Bill-image upload validation.

Every uploaded image is treated as untrusted bytes:
- the real format is derived from magic bytes, never from the client's
  filename or declared content type;
- only JPEG, PNG and WebP are accepted;
- decoding runs through Pillow with a decompression-bomb guard so corrupted
  or hostile files raise a clean, client-safe error instead of crashing;
- nothing is written to disk, so there is no temporary file to clean up and
  no image is retained after the request completes.

Upload contents are never executed and never sent anywhere.
"""

from __future__ import annotations

import io
import logging

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.errors import ImageValidationError, PayloadTooLargeError

logger = logging.getLogger(__name__)

#: Guard against decompression bombs (Pillow's own default is ~178 megapixels).
Image.MAX_IMAGE_PIXELS = 50_000_000

SUPPORTED_FORMAT_LABELS = ("JPEG", "PNG", "WebP")


def _sniff_format(data: bytes) -> str | None:
    """Return the Pillows-style format name based on magic bytes, or ``None``."""

    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WebP"
    return None


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks, aborting as soon as the size limit is crossed.

    Limits the amount of memory a hostile client can make the process allocate.
    """

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError("The uploaded image exceeds the configured size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_image(data: bytes, *, max_dimension_px: int) -> Image.Image:
    """Validate magic bytes and safely decode the image, or raise a client-safe error."""

    if not data:
        raise ImageValidationError(message="The uploaded file is empty.")

    detected = _sniff_format(data)
    if detected is None:
        raise ImageValidationError(
            code="unsupported_image_format",
            message="The file is not a supported image format. "
            "Supported formats are JPEG, PNG and WebP.",
        )

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.load()
            width, height = probe.size
            image = probe.convert("RGB")
        image.format_ = detected  # type: ignore[attr-defined] - bookkeeping only
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.info("upload rejected: undecodable image (%d bytes)", len(data))
        raise ImageValidationError(
            code="corrupt_image",
            message="The image could not be opened; it may be corrupt. "
            "Please retry with a clearer photo or enter the bill number manually.",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard for decode bombs
        logger.info("upload rejected: decoder refused image (%d bytes)", len(data))
        raise ImageValidationError(
            code="corrupt_image",
            message="The image could not be opened; it may be corrupt.",
        ) from exc

    if max(width, height) > max_dimension_px:
        raise ImageValidationError(
            code="image_dimensions_exceed_limit",
            message=f"The image is too large: {width}x{height} pixels exceeds the "
            f"maximum side of {max_dimension_px} pixels.",
        )

    return image
