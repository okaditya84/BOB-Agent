"""Password-strength evaluation (server-side, dependency-free).

Estimates strength from length, character-class diversity and a small common-password
blocklist, returning a 0-4 score with actionable feedback. Mirrors the client-side
meter so the verdict is consistent and cannot be bypassed by tampering with the page.
"""

from __future__ import annotations

import math
import re

# A tiny blocklist of the most common/breached passwords (illustrative; production
# would use a large breached-password set, e.g. HaveIBeenPwned k-anonymity).
_COMMON = {
    "password", "123456", "123456789", "12345678", "qwerty", "abc123", "password1",
    "111111", "123123", "admin", "letmein", "welcome", "monkey", "iloveyou",
    "bankofbaroda", "baroda", "bobai",
}

_LABELS = {0: "very weak", 1: "weak", 2: "fair", 3: "strong", 4: "very strong"}


def evaluate(password: str) -> dict:
    pw = password or ""
    feedback: list[str] = []

    classes = sum(bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    pool = (26 if re.search(r"[a-z]", pw) else 0) + (26 if re.search(r"[A-Z]", pw) else 0) \
        + (10 if re.search(r"\d", pw) else 0) + (33 if re.search(r"[^A-Za-z0-9]", pw) else 0)
    entropy_bits = round(len(pw) * math.log2(pool), 1) if pool else 0.0

    if pw.lower() in _COMMON:
        return {"score": 0, "label": "very weak", "entropy_bits": entropy_bits,
                "acceptable": False, "feedback": ["This is a commonly used password — choose another."]}

    if len(pw) < 8:
        feedback.append("Use at least 8 characters.")
    if classes < 3:
        feedback.append("Mix upper/lowercase, numbers and symbols.")
    if re.search(r"(.)\1\1", pw):
        feedback.append("Avoid repeated characters.")

    if entropy_bits < 28 or len(pw) < 8:
        score = 1
    elif entropy_bits < 40:
        score = 2
    elif entropy_bits < 60:
        score = 3
    else:
        score = 4
    if classes <= 1:
        score = min(score, 1)

    return {
        "score": score, "label": _LABELS[score], "entropy_bits": entropy_bits,
        "acceptable": score >= 2 and len(pw) >= 8,
        "feedback": feedback or ["Looks good."],
    }
