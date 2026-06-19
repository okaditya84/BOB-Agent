"""Password-strength + signup-flow tests."""

from __future__ import annotations

from bobai_identity.auth import password


def test_password_rejects_common():
    r = password.evaluate("password")
    assert r["acceptable"] is False
    assert r["score"] == 0


def test_password_rejects_short():
    assert password.evaluate("Ab1!")["acceptable"] is False


def test_password_accepts_strong():
    r = password.evaluate("Tr0ub4dour&3xplore")
    assert r["acceptable"] is True
    assert r["score"] >= 3


def test_password_entropy_increases_with_length():
    short = password.evaluate("Ab1!xy")["entropy_bits"]
    long = password.evaluate("Ab1!xyAb1!xyAb1!")["entropy_bits"]
    assert long > short
