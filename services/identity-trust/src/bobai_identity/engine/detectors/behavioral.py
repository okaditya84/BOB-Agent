"""Behavioral-biometrics drift detector (continuous authentication).

Compares this session's passive behavioral features against the user's rolling
baseline. Large drift suggests a different human is at the keyboard — the core of
post-login continuous validation. Used as a risk input, never a hard block.
"""

from __future__ import annotations

from ...schemas import AuthEvent
from ...store.db import UserProfile
from . import DetectorResult

# Natural session-to-session variation we tolerate before raising risk.
_TOLERANCE = 0.25


def _features(event: AuthEvent) -> dict[str, float]:
    b = event.behavioral
    if b is None:
        return {}
    raw = {
        "typing_speed_cpm": b.typing_speed_cpm,
        "avg_dwell_ms": b.avg_dwell_ms,
        "avg_flight_ms": b.avg_flight_ms,
        "mouse_velocity": b.mouse_velocity,
        "paste_ratio": b.paste_ratio,
    }
    return {k: v for k, v in raw.items() if v is not None}


def detect(event: AuthEvent, profile: UserProfile) -> DetectorResult | None:
    feats = _features(event)
    if not feats:
        return None

    baseline = profile.behavioral_baseline
    if not baseline:
        return DetectorResult(0.0, "Behavioral baseline still being learned.", {"learning": True})

    deviations: dict[str, float] = {}
    for k, v in feats.items():
        base = baseline.get(k)
        if base is None or base <= 0:
            continue
        deviations[k] = min(1.0, abs(v - base) / base)
    if not deviations:
        return DetectorResult(0.0, "No comparable behavioral features yet.", {"learning": True})

    mean_dev = sum(deviations.values()) / len(deviations)
    raw = max(0.0, min(1.0, (mean_dev - _TOLERANCE) / (1.0 - _TOLERANCE)))
    worst = max(deviations, key=deviations.get)

    if raw > 0:
        detail = f"Behavioral pattern deviates from baseline (largest: {worst}, {deviations[worst]*100:.0f}%)."
    else:
        detail = "Behavioral pattern consistent with the user's baseline."
    return DetectorResult(raw, detail, {"deviations": {k: round(v, 2) for k, v in deviations.items()}})
