"""API-level tests via FastAPI TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bobai_identity import config
from conftest import BASE_TS, MUMBAI, TOKYO


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("IDTRUST_DB_PATH", str(db))
    monkeypatch.setenv("IDTRUST_SECRET", "test-secret")
    config.get_settings.cache_clear()
    from bobai_identity.main import app

    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()


def _event(ts, device, geo):
    return {
        "user_id": "api-user",
        "event_type": "login",
        "timestamp": ts,
        "device_fingerprint": device,
        "geo": geo,
    }


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_evaluate_endpoint_returns_decision(client):
    r = client.post("/v1/risk/evaluate", json=_event(BASE_TS, "dev-1", MUMBAI))
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["risk_score"] <= 1
    assert body["action"] in {"allow", "monitor", "step_up", "deny"}
    assert body["signals"]


def test_evaluate_impossible_travel_via_api(client):
    client.post("/v1/risk/evaluate", json=_event(BASE_TS, "dev-A", MUMBAI))
    r = client.post("/v1/risk/evaluate", json=_event(BASE_TS + 1200, "dev-B", TOKYO))
    body = r.json()
    assert body["action"] in {"step_up", "deny"}


def test_audit_verify_endpoint(client):
    client.post("/v1/risk/evaluate", json=_event(BASE_TS, "dev-1", MUMBAI))
    r = client.get("/v1/audit/verify")
    assert r.json()["intact"] is True


def test_webauthn_register_begin_returns_challenge(client):
    r = client.post("/v1/webauthn/register/begin", json={"user_id": "api-user"})
    assert r.status_code == 200
    assert "challenge" in r.json()


def test_webauthn_stepup_without_passkey_fails(client):
    r = client.post("/v1/webauthn/authenticate/begin", json={"user_id": "nobody"})
    assert r.status_code == 400  # no registered passkeys → cannot step up


def test_analytics_summary_endpoint(client):
    client.post("/v1/risk/evaluate", json=_event(BASE_TS, "dev-1", MUMBAI))
    body = client.get("/v1/analytics/summary").json()
    assert body["total_events"] >= 1
    assert "by_action" in body


def test_dashboard_served(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "BOBAI" in r.text


def test_login_page_served(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "Secure Access" in r.text


def test_public_config(client):
    r = client.get("/v1/config")
    assert r.status_code == 200
    assert "bobai_ui_url" in r.json()


def test_portal_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "BOBAI" in r.text
    assert "For Customers" in r.text


def test_config_has_all_surface_urls(client):
    c = client.get("/v1/config").json()
    assert {"bobai_ui_url", "ekyc_url", "dashboard_url", "login_url", "signup_url"} <= set(c)


def test_signup_page_served(client):
    r = client.get("/signup")
    assert r.status_code == 200
    assert "Create" in r.text


def test_password_check_endpoint(client):
    r = client.post("/v1/auth/password/check", json={"password": "password"})
    assert r.status_code == 200
    assert r.json()["acceptable"] is False


def test_signup_rejects_weak_password(client):
    r = client.post("/v1/auth/signup", json={
        "password": "123456",
        "event": {"user_id": "newbie", "event_type": "account_opening",
                  "timestamp": BASE_TS, "device_fingerprint": "d", "geo": MUMBAI},
    })
    body = r.json()
    assert body["created"] is False


def test_signup_succeeds_with_strong_password(client):
    r = client.post("/v1/auth/signup", json={
        "password": "Tr0ub4dour&3xplore",
        "event": {"user_id": "newcustomer", "event_type": "account_opening",
                  "timestamp": BASE_TS, "device_fingerprint": "d2", "geo": MUMBAI},
    })
    body = r.json()
    assert body["created"] is True
    assert "risk" in body
