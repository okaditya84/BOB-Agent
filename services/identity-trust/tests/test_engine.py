"""Behavioural tests for the risk engine — the claims we'll demo to the jury."""

from __future__ import annotations

from bobai_identity.schemas import AuthEvent, EventType, RiskAction, RiskBand

from conftest import BASE_TS, MUMBAI, TOKYO


def _login(user_id="u1", ts=BASE_TS, device="trusted-laptop", geo=MUMBAI, **kw) -> AuthEvent:
    return AuthEvent(
        user_id=user_id,
        event_type=kw.pop("event_type", EventType.LOGIN),
        timestamp=ts,
        device_fingerprint=device,
        geo=geo,
        **kw,
    )


def test_returning_user_known_device_is_low_friction(engine):
    # First login establishes the baseline (device + location are learned).
    engine.evaluate(_login(ts=BASE_TS))
    # Same device, same place, one hour later → should be low risk / allowed.
    d = engine.evaluate(_login(ts=BASE_TS + 3600))
    assert d.action == RiskAction.ALLOW
    assert d.band == RiskBand.LOW
    device_signal = next(s for s in d.signals if s.name == "device")
    assert device_signal.raw == 0.0  # recognised device contributes no risk


def test_impossible_travel_triggers_step_up(engine):
    engine.evaluate(_login(ts=BASE_TS, device="laptop-A", geo=MUMBAI))
    # 20 minutes later, from Tokyo, on a brand-new device.
    d = engine.evaluate(_login(ts=BASE_TS + 1200, device="phone-B", geo=TOKYO))
    assert d.action in (RiskAction.STEP_UP, RiskAction.DENY)
    assert d.band in (RiskBand.HIGH, RiskBand.CRITICAL)
    assert any("Impossible travel" in rc for rc in d.reason_codes)
    geo_signal = next(s for s in d.signals if s.name == "geo")
    assert geo_signal.raw == 1.0


def test_new_device_raises_risk_versus_known(engine):
    engine.evaluate(_login(ts=BASE_TS, device="laptop-A"))
    known = engine.evaluate(_login(ts=BASE_TS + 3600, device="laptop-A"))
    new = engine.evaluate(_login(ts=BASE_TS + 7200, device="laptop-Z"))
    assert new.risk_score > known.risk_score
    assert next(s for s in new.signals if s.name == "device").raw == 0.70


def test_decision_is_explainable(engine):
    d = engine.evaluate(_login())
    assert d.signals, "every decision must carry its signal breakdown"
    assert all(s.detail for s in d.signals), "every signal must have a reason"
    assert d.reason_codes
    assert d.policy_rationale


def test_account_recovery_is_more_sensitive_than_login(engine):
    engine.evaluate(_login(ts=BASE_TS))
    login = engine.evaluate(_login(ts=BASE_TS + 3600))
    recovery = engine.evaluate(
        _login(ts=BASE_TS + 7200, event_type=EventType.ACCOUNT_RECOVERY)
    )
    assert recovery.risk_score > login.risk_score


def test_high_risk_event_does_not_learn_device(engine):
    engine.evaluate(_login(ts=BASE_TS, device="laptop-A", geo=MUMBAI))
    # Impossible-travel login on a new device → step-up; device must NOT be trusted.
    engine.evaluate(_login(ts=BASE_TS + 1200, device="phone-B", geo=TOKYO))
    profile = engine.store.get_profile("u1")
    new_token = engine.store.tokenize("phone-B")
    assert new_token not in profile.known_devices
