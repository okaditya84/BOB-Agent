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
