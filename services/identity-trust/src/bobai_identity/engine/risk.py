"""The risk orchestrator: gather detector signals, blend, decide, persist, learn."""

from __future__ import annotations

import uuid

from ..config import Settings
from ..schemas import AuthEvent, RiskAction, RiskDecision, SignalContribution
from ..store.db import Store, UserProfile
from . import policy
from .detectors import behavioral, context, device, geo
from .detectors.anomaly import RiskModel

# Base detector weights (renormalised over whichever detectors are active per-event).
_WEIGHTS = {
    "geo": 0.22,
    "device": 0.20,
    "behavioral": 0.15,
    "context": 0.18,
    "anomaly": 0.25,
}

# How fast the behavioral baseline tracks new sessions.
_EWMA_ALPHA = 0.3

# Behavioral feature names tracked in the baseline.
_BEHAVIORAL_FEATURES = [
    "typing_speed_cpm", "avg_dwell_ms", "avg_flight_ms", "mouse_velocity", "paste_ratio",
]


class RiskEngine:
    def __init__(self, store: Store, settings: Settings, model: RiskModel | None = None) -> None:
        self.store = store
        self.settings = settings
        self.model = model or RiskModel()

    def evaluate(self, event: AuthEvent) -> RiskDecision:
        profile = self.store.get_profile(event.user_id)
        device_token = self.store.tokenize(event.device_fingerprint)

        geo_r = geo.detect(event, profile, self.settings)
        dev_r = device.detect(event, profile, device_token)
        beh_r = behavioral.detect(event, profile)
        ctx_r = context.detect(event, self.settings)

        features = {
            "amount_norm": min(event.amount or 0.0, 1_000_000.0) / 1_000_000.0,
            "device_new": 1.0 if dev_r.data.get("new") else 0.0,
            "geo_speed_norm": geo_r.raw if geo_r else 0.0,
            "behavioral_dev": beh_r.raw if beh_r else 0.0,
            "sensitivity": ctx_r.raw,
        }
        ml_r = self.model.score(features)

        active = {"device": dev_r, "context": ctx_r, "anomaly": ml_r}
        if geo_r is not None:
            active["geo"] = geo_r
        if beh_r is not None:
            active["behavioral"] = beh_r

        total_w = sum(_WEIGHTS[k] for k in active)
        contributions: list[SignalContribution] = []
        score = 0.0
        for name, res in active.items():
            w = _WEIGHTS[name] / total_w
            contrib = w * res.raw
            score += contrib
            contributions.append(
                SignalContribution(
                    name=name,
                    weight=round(w, 3),
                    raw=round(res.raw, 3),
                    contribution=round(contrib, 3),
                    detail=res.detail,
                    data=res.data,
                )
            )
        score = min(1.0, score)

        band, action, required_aal, rationale = policy.decide(score, self.settings)

        ranked = sorted(contributions, key=lambda c: c.contribution, reverse=True)
        reason_codes = [c.detail for c in ranked if c.raw > 0]
        if not reason_codes:
            reason_codes = ["No risk indicators; behaviour consistent with the user's norm."]

        decision = RiskDecision(
            decision_id=uuid.uuid4().hex,
            user_id=event.user_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            risk_score=round(score, 4),
            band=band,
            action=action,
            required_aal=required_aal,
            reason_codes=reason_codes,
            signals=contributions,
            policy_rationale=rationale,
        )

        payload = decision.model_dump(mode="json")
        self.store.save_decision(payload)
        self.store.append_audit(
            "risk_decision",
            decision.decision_id,
            {
                "user_id": event.user_id,
                "event_type": event.event_type.value,
                "risk_score": decision.risk_score,
                "action": action.value,
            },
            event.timestamp,
        )

        # Learn only from events we implicitly trust (low/moderate risk). High-risk or
        # denied events do NOT update the baseline until step-up is verified.
        if action in (RiskAction.ALLOW, RiskAction.MONITOR):
            self._learn(profile, event, device_token, trust_device=True)
        else:
            # Still count the event, but don't trust its device/location yet.
            profile.event_count += 1
            self.store.save_profile(profile)

        return decision

    def trust_event(self, event: AuthEvent) -> None:
        """Promote an event's device/location to trusted — call after a verified step-up."""
        profile = self.store.get_profile(event.user_id)
        device_token = self.store.tokenize(event.device_fingerprint)
        self._learn(profile, event, device_token, trust_device=True)

    def _learn(
        self, profile: UserProfile, event: AuthEvent, device_token: str | None, trust_device: bool
    ) -> None:
        if event.geo is not None:
            profile.last_lat = event.geo.lat
            profile.last_lon = event.geo.lon
        profile.last_ts = event.timestamp

        if trust_device and device_token and device_token not in profile.known_devices:
            profile.known_devices.append(device_token)

        if event.behavioral is not None:
            for fname in _BEHAVIORAL_FEATURES:
                val = getattr(event.behavioral, fname)
                if val is None:
                    continue
                old = profile.behavioral_baseline.get(fname)
                profile.behavioral_baseline[fname] = (
                    val if old is None else (1 - _EWMA_ALPHA) * old + _EWMA_ALPHA * val
                )

        profile.event_count += 1
        self.store.save_profile(profile)
