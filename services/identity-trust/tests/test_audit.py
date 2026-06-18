"""The audit log must be tamper-evident (hash-chained)."""

from __future__ import annotations

from bobai_identity.schemas import AuthEvent, EventType

from conftest import BASE_TS, MUMBAI


def _ev(ts):
    return AuthEvent(
        user_id="u1", event_type=EventType.LOGIN, timestamp=ts,
        device_fingerprint="laptop-A", geo=MUMBAI,
    )


def test_audit_chain_intact_after_decisions(engine):
    for i in range(5):
        engine.evaluate(_ev(BASE_TS + i * 3600))
    result = engine.store.verify_audit_chain()
    assert result["intact"] is True
    assert result["entries"] == 5


def test_audit_chain_detects_tampering(engine):
    for i in range(3):
        engine.evaluate(_ev(BASE_TS + i * 3600))
    # Tamper with the first audit entry directly in the DB.
    engine.store._conn.execute(  # noqa: SLF001 — intentional tamper in test
        "UPDATE audit_log SET payload_hash = 'tampered' WHERE seq = 1"
    )
    engine.store._conn.commit()
    result = engine.store.verify_audit_chain()
    assert result["intact"] is False
    assert result["broken_at_seq"] == 1


def test_pii_is_tokenised_not_stored_raw(engine):
    token = engine.store.tokenize("device-fingerprint-xyz")
    assert token is not None
    assert token != "device-fingerprint-xyz"
    assert len(token) == 64  # sha256 hex
    # Deterministic: same input → same token (so repeat devices match).
    assert token == engine.store.tokenize("device-fingerprint-xyz")
