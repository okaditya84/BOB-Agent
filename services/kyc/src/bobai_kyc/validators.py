"""Document-number validators — Aadhaar (Verhoeff), PAN, and helpers.

These are exact, deterministic checks (no ML): a number that fails its checksum or
format is structurally invalid and a strong fraud signal.
"""

from __future__ import annotations

import re

# ---- Verhoeff checksum (used by UIDAI for the 12-digit Aadhaar number) ----
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_AADHAAR_RE = re.compile(r"^\d{12}$")


def digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def verhoeff_check(number: str) -> bool:
    """True if the digit string passes the Verhoeff checksum."""
    digits = digits_only(number)
    if not digits:
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def validate_aadhaar(number: str) -> tuple[bool, str]:
    digits = digits_only(number)
    if not _AADHAAR_RE.match(digits):
        return False, "Aadhaar must be exactly 12 digits."
    if digits[0] in "01":
        return False, "Aadhaar cannot start with 0 or 1."
    if not verhoeff_check(digits):
        return False, "Aadhaar failed the Verhoeff checksum (likely invalid/forged)."
    return True, "Valid Aadhaar number format and checksum."


def validate_pan(pan: str) -> tuple[bool, str]:
    p = (pan or "").strip().upper()
    if not _PAN_RE.match(p):
        return False, "PAN must match format AAAAA9999A."
    # 4th char encodes holder type; 'P' = individual (common for retail KYC).
    return True, f"Valid PAN format (holder type '{p[3]}')."
