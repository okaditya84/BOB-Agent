"""Declarative risk policy: map a blended risk score to an action + assurance level.

Tiers are mapped to NIST SP 800-63B AAL and framed against the RBI (Authentication
Mechanisms for Digital Payment Transactions) Directions, 2025, which explicitly
endorse risk-based step-up authentication.
"""

from __future__ import annotations

from ..config import Settings
from ..schemas import AAL, RiskAction, RiskBand


def decide(score: float, settings: Settings) -> tuple[RiskBand, RiskAction, AAL, str]:
    medium = settings.threshold_step_up / 2.0

    if score >= settings.threshold_deny:
        return (
            RiskBand.CRITICAL,
            RiskAction.DENY,
            AAL.AAL3,
            "Risk exceeds the deny threshold; access blocked pending manual review "
            "(risk-based control per RBI 2025 Authentication Directions).",
        )
    if score >= settings.threshold_step_up:
        return (
            RiskBand.HIGH,
            RiskAction.STEP_UP,
            AAL.AAL2,
            "Elevated risk: phishing-resistant step-up (passkey/WebAuthn, NIST AAL2) "
            "required before proceeding, per RBI 2025 risk-based step-up guidance.",
        )
    if score >= medium:
        return (
            RiskBand.MEDIUM,
            RiskAction.MONITOR,
            AAL.AAL1,
            "Moderate risk: access allowed at AAL1 but flagged for monitoring/review.",
        )
    return (
        RiskBand.LOW,
        RiskAction.ALLOW,
        AAL.AAL1,
        "Low risk: frictionless access at AAL1 (no added authentication friction).",
    )
