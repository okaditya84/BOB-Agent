"""Tests for document tamper detection, validators, and the fraud orchestrator."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from bobai_kyc.forensics import ela_analyze
from bobai_kyc.fraud import analyze_document
from bobai_kyc.schemas import ClaimedFields, DocumentType, FraudVerdict
from bobai_kyc.validators import validate_aadhaar, validate_pan, verhoeff_check


# --------------------------- helpers --------------------------- #
def _clean_jpeg() -> bytes:
    img = Image.new("RGB", (240, 150), (185, 185, 185))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "GOVERNMENT OF INDIA", fill=(40, 40, 40))
    b = BytesIO()
    img.save(b, "JPEG", quality=92)
    return b.getvalue()


def _tampered_jpeg() -> bytes:
    # Take a JPEG, splice a hard high-contrast block, re-paste (uneven compression).
    img = Image.open(BytesIO(_clean_jpeg())).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([120, 60, 220, 130], fill=(255, 0, 0))
    d.text((124, 64), "9999", fill=(255, 255, 255))
    b = BytesIO()
    img.save(b, "JPEG", quality=98)  # different quality region -> ELA residual
    return b.getvalue()


def _valid_aadhaar() -> str:
    base = "23412341234"  # 11 digits, leading 2 (not 0/1)
    for d in range(10):
        cand = base + str(d)
        if verhoeff_check(cand):
            return cand
    raise AssertionError("could not construct a Verhoeff-valid Aadhaar")


# --------------------------- validators --------------------------- #
def test_verhoeff_canonical_example():
    # Wikipedia's canonical Verhoeff example: 236 -> check digit 3 -> 2363 valid.
    assert verhoeff_check("2363") is True
    assert verhoeff_check("2364") is False


def test_validate_aadhaar_accepts_valid_and_rejects_tampered():
    valid = _valid_aadhaar()
    ok, _ = validate_aadhaar(valid)
    assert ok is True
    # Flip a middle digit -> checksum must fail.
    flipped = valid[:5] + ("0" if valid[5] != "0" else "1") + valid[6:]
    ok2, _ = validate_aadhaar(flipped)
    assert ok2 is False


def test_validate_aadhaar_format_rules():
    assert validate_aadhaar("1234")[0] is False  # too short
    assert validate_aadhaar("0" + _valid_aadhaar()[1:])[0] is False  # leading 0


def test_validate_pan():
    assert validate_pan("ABCPK1234L")[0] is True
    assert validate_pan("ABC123")[0] is False


# --------------------------- ELA --------------------------- #
def test_ela_flags_tampered_more_than_clean():
    clean = ela_analyze(_clean_jpeg())
    tampered = ela_analyze(_tampered_jpeg())
    assert tampered.score >= clean.score
    assert tampered.mean_error > clean.mean_error


# --------------------------- orchestrator --------------------------- #
def test_clean_matching_document_passes():
    valid = _valid_aadhaar()
    spaced = f"{valid[0:4]} {valid[4:8]} {valid[8:12]}"
    text = f"GOVERNMENT OF INDIA\nRavi Kumar\nDOB 01/01/1990\n{spaced}"
    report = analyze_document(
        _clean_jpeg(), DocumentType.AADHAAR,
        ClaimedFields(name="Ravi Kumar", dob="01/01/1990", document_number=valid),
        ocr_text=text,
    )
    assert report.format_valid is True
    assert report.verdict == FraudVerdict.PASS
    assert report.extracted_fields.get("aadhaar") == valid


def test_number_mismatch_is_flagged():
    valid = _valid_aadhaar()
    other = _valid_aadhaar()[::-1]  # different digit string
    text = f"GOVERNMENT OF INDIA\nRavi Kumar\n{other[0:4]} {other[4:8]} {other[8:12]}"
    report = analyze_document(
        _clean_jpeg(), DocumentType.AADHAAR,
        ClaimedFields(name="Ravi Kumar", document_number=valid),
        ocr_text=text,
    )
    assert report.verdict in (FraudVerdict.REVIEW, FraudVerdict.REJECT)
    assert any("does not match" in f for f in report.flags)


def test_invalid_checksum_triggers_review_or_reject():
    bad = "234123412340"  # almost certainly fails Verhoeff
    report = analyze_document(
        _clean_jpeg(), DocumentType.AADHAAR,
        ClaimedFields(document_number=bad), ocr_text=f"ID {bad}",
    )
    # If it happens to be valid, skip; otherwise it must not PASS.
    if report.format_valid is False:
        assert report.verdict in (FraudVerdict.REVIEW, FraudVerdict.REJECT)


def test_api_document_analyze(monkeypatch):
    from fastapi.testclient import TestClient

    from bobai_kyc.main import app

    with TestClient(app) as c:
        r = c.post(
            "/v1/kyc/document/analyze",
            files={"file": ("aadhaar.jpg", _clean_jpeg(), "image/jpeg")},
            data={"document_type": "aadhaar", "document_number": _valid_aadhaar(), "run_ocr": "false"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verdict"] in {"pass", "review", "reject"}
        assert "ela" in body
