"""Analytics / access-log tests."""

from __future__ import annotations

from bobai_identity.schemas import AuthEvent, EventType

from conftest import BASE_TS, MUMBAI, TOKYO


def _login(uid, ts, device, geo):
    return AuthEvent(user_id=uid, event_type=EventType.LOGIN, timestamp=ts,
                     device_fingerprint=device, geo=geo)


def test_access_recorded_with_geo_and_summary(engine):
    engine.evaluate(_login("u1", BASE_TS, "A", MUMBAI))
    engine.evaluate(_login("u1", BASE_TS + 1200, "B", TOKYO))   # impossible travel
    engine.evaluate(_login("u2", BASE_TS, "C", MUMBAI))

    summary = engine.store.analytics_summary()
    assert summary["total_events"] == 3
    assert summary["distinct_users"] == 2
    assert sum(summary["by_action"].values()) == 3
    assert summary["top_reasons"]  # at least one reason captured

    rows = engine.store.access_recent()
    assert len(rows) == 3
    assert all(r["lat"] is not None for r in rows)  # browser geo recorded
    # The impossible-travel event should have been a step-up or deny.
    assert any(r["action"] in ("step_up", "deny") for r in rows)
