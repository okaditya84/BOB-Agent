"""Vision document-classifier tests (Groq call mocked — no network)."""

from __future__ import annotations

import json

import pytest

from bobai_kyc.vision import DocumentVisionClassifier


def test_unavailable_without_key():
    c = DocumentVisionClassifier("m", "http://x", api_key=None)
    assert c.available is False
    out = c.classify(b"img")
    assert out["available"] is False


def test_classifies_aadhaar(monkeypatch):
    c = DocumentVisionClassifier("m", "http://groq.test", api_key="k")

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "is_identity_document": True, "document_type": "aadhaar",
                "confidence": 0.97,
                "extracted": {"name": "Aditya", "dob": "08/02/2003", "document_number": "7302 9996 1766"},
                "reason": "Government of India Aadhaar with 12-digit number",
            })}}]}

    monkeypatch.setattr("bobai_kyc.vision.httpx.post", lambda *a, **k: _Resp())
    out = c.classify(b"img")
    assert out["ok"] is True
    assert out["is_identity_document"] is True
    assert out["document_type"] == "aadhaar"
    assert out["extracted"]["name"] == "Aditya"


def test_rejects_non_id(monkeypatch):
    c = DocumentVisionClassifier("m", "http://groq.test", api_key="k")

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "is_identity_document": False, "document_type": "other",
                "confidence": 0.9, "extracted": {}, "reason": "Conference badge, not an ID",
            })}}]}

    monkeypatch.setattr("bobai_kyc.vision.httpx.post", lambda *a, **k: _Resp())
    out = c.classify(b"img")
    assert out["is_identity_document"] is False
    assert out["document_type"] == "other"


def test_handles_bad_json(monkeypatch):
    c = DocumentVisionClassifier("m", "http://groq.test", api_key="k")

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr("bobai_kyc.vision.httpx.post", lambda *a, **k: _Resp())
    out = c.classify(b"img")
    assert out["available"] is True and out["ok"] is False
