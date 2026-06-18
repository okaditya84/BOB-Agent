"""Document-check logic + API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bobai_kyc.matcher import check


def test_check_empty_submission_is_incomplete(kb):
    req = kb.requirements("bob_super_savings_account")
    result = check(req, submitted=[])
    assert result.required_complete is False
    assert result.completeness == 0.0
    assert result.missing_summary


def test_check_pick_one_satisfied_by_single_ovd(kb):
    req = kb.requirements("bob_super_savings_account")
    result = check(req, submitted=["Aadhaar Card"])
    ovd = next(g for g in result.groups if g.label.startswith("Identity & address"))
    assert ovd.complete is True
    assert ovd.satisfied


def test_check_completeness_increases_with_more_docs(kb):
    req = kb.requirements("bob_super_savings_account")
    few = check(req, submitted=["Aadhaar Card"])
    more = check(
        req,
        submitted=[
            "Aadhaar Card", "PAN Card", "2 recent passport-size colour photographs",
            "Duly filled and signed Account Opening Form", "Specimen signature",
        ],
    )
    assert more.completeness > few.completeness


@pytest.fixture
def client():
    from bobai_kyc.main import app

    with TestClient(app) as c:
        yield c


def test_api_products(client):
    r = client.get("/v1/kyc/products")
    assert r.status_code == 200
    assert any(p["id"] == "home_loan" for p in r.json())


def test_api_requirements(client):
    r = client.get("/v1/kyc/requirements", params={"product_id": "home_loan", "profile": "salaried"})
    assert r.status_code == 200
    assert r.json()["product"]["id"] == "home_loan"


def test_api_requirements_unknown_404(client):
    r = client.get("/v1/kyc/requirements", params={"product_id": "nope"})
    assert r.status_code == 404


def test_api_check(client):
    r = client.post(
        "/v1/kyc/check",
        json={"product_id": "bob_super_savings_account", "submitted": ["Aadhaar", "PAN"]},
    )
    assert r.status_code == 200
    assert 0 <= r.json()["completeness"] <= 1
