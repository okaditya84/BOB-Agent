"""OCR layer: a pluggable engine plus field extraction from recognised text.

`TesseractEngine` is a real backend (system Tesseract via pytesseract). The engine
is an interface so a heavier backend (PaddleOCR/docTR) can be swapped in without
touching callers. Field extraction is pure-text and independently testable.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Protocol


class OCREngine(Protocol):
    def image_to_text(self, image_bytes: bytes) -> str: ...


class TesseractEngine:
    """Real OCR via the system Tesseract binary. Imports lazily so the service
    still starts (for non-OCR endpoints) if the binary/lib is absent."""

    def image_to_text(self, image_bytes: bytes) -> str:
        import pytesseract
        from PIL import Image

        return pytesseract.image_to_string(Image.open(BytesIO(image_bytes)))


_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_DOB_RE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")
# Single literal spaces only — using \s here would glue digits across line breaks
# (e.g. a DOB year on the previous line) into a false 12-digit match.
_AADHAAR_SPACED_RE = re.compile(r"\b(\d{4} \d{4} \d{4})\b")
_AADHAAR_PLAIN_RE = re.compile(r"\b(\d{12})\b")


def extract_fields(text: str) -> dict[str, str]:
    """Pull structured identifiers out of raw OCR text."""
    out: dict[str, str] = {}
    if not text:
        return out

    pan = _PAN_RE.search(text.upper())
    if pan:
        out["pan"] = pan.group(0)

    spaced = _AADHAAR_SPACED_RE.search(text)
    if spaced:
        out["aadhaar"] = re.sub(r"\s", "", spaced.group(1))
    else:
        plain = _AADHAAR_PLAIN_RE.search(text)
        if plain:
            out["aadhaar"] = plain.group(1)

    dob = _DOB_RE.search(text)
    if dob:
        out["dob"] = dob.group(1)

    return out
