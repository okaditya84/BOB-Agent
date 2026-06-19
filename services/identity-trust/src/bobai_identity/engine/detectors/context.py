"""Contextual risk: action sensitivity, off-hours, transaction size, network origin."""

from __future__ import annotations

from datetime import datetime, timezone

from ...schemas import AuthEvent, EventType
from . import DetectorResult

# Inherent sensitivity of each action type (0..1 base risk).
_SENSITIVITY = {
    EventType.LOGIN: 0.05,
    EventType.ACCOUNT_OPENING: 0.30,  # new-account fraud is high-stakes
    EventType.TRANSACTION: 0.10,
    EventType.BENEFICIARY_ADD: 0.25,
    EventType.PROFILE_CHANGE: 0.20,
    EventType.ACCOUNT_RECOVERY: 0.45,
    EventType.PRIVILEGE_CHANGE: 0.50,  # insider / privileged-access action
    EventType.KYC_SUBMISSION: 0.20,
}


def detect(event: AuthEvent, settings) -> DetectorResult:
    raw = _SENSITIVITY.get(event.event_type, 0.10)
    reasons: list[str] = [f"{event.event_type.value} action"]

    # Off-hours (00:00–05:00 UTC as a simple proxy) raises risk for sensitive actions.
    hour = datetime.fromtimestamp(event.timestamp, tz=timezone.utc).hour
    if hour < 5:
        raw += 0.15
        reasons.append("off-hours access")

    # Large transactions raise risk.
    if event.event_type == EventType.TRANSACTION and event.amount:
        if event.amount >= 500_000:
            raw += 0.40
            reasons.append(f"very large amount (₹{event.amount:,.0f})")
        elif event.amount >= 100_000:
            raw += 0.20
            reasons.append(f"large amount (₹{event.amount:,.0f})")

    # Anonymised / hosting-origin network is a strong fraud indicator.
    if event.is_tor:
        raw += 0.40
        reasons.append("Tor exit node")
    if event.is_datacenter:
        raw += 0.25
        reasons.append("datacenter/hosting IP (atypical for retail customers)")

    raw = min(1.0, raw)
    return DetectorResult(raw, "Contextual factors: " + ", ".join(reasons) + ".", {"hour_utc": hour})
