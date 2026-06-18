"""New-device detection. Operates on the HMAC token, never the raw fingerprint."""

from __future__ import annotations

from ...schemas import AuthEvent
from ...store.db import UserProfile
from . import DetectorResult


def detect(event: AuthEvent, profile: UserProfile, device_token: str | None) -> DetectorResult:
    if device_token is None:
        return DetectorResult(0.30, "No device fingerprint supplied; device cannot be trusted.", {"new": None})

    if not profile.known_devices:
        # First device for a brand-new user — expected during onboarding, low risk.
        return DetectorResult(0.15, "First device observed for this user.", {"new": True, "onboarding": True})

    if device_token in profile.known_devices:
        return DetectorResult(0.0, "Recognised, previously-trusted device.", {"new": False})

    return DetectorResult(
        0.70,
        "Access from a new, unrecognised device.",
        {"new": True, "known_device_count": len(profile.known_devices)},
    )
