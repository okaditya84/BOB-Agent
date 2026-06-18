"""Tests for the dynamic KB resolver against the real BoB data."""

from __future__ import annotations


def _labels(req):
    return [g.label for g in req.groups]


def test_products_discovered_dynamically(kb):
    ids = {p.id for p in kb.list_products()}
    # Across categories: account sub-type, loan, other product.
    assert "bob_super_savings_account" in ids
    assert "home_loan" in ids
    assert "ppf_account" in ids
    assert "nre_savings_account" in ids
    # Informational-only entries are NOT products.
    assert "nri_banking_overview" not in ids


def test_core_kyc_always_present_and_pick_one(kb):
    req = kb.requirements("bob_super_savings_account")
    ovd = next(g for g in req.groups if g.label.startswith("Identity & address"))
    assert ovd.pick_one is True
    assert ovd.required is True
    assert any("Aadhaar" in d for d in ovd.documents)
    tax = next(g for g in req.groups if g.label == "Tax ID")
    assert tax.pick_one is True


def test_home_loan_salaried_profile(kb):
    req = kb.requirements("home_loan", profile="salaried")
    assert "salaried" in req.available_profiles
    assert {"self_employed", "nri", "pensioner"} <= set(req.available_profiles)
    salaried_group = next(g for g in req.groups if "salaried" in g.label.lower())
    assert any("salary" in d.lower() for d in salaried_group.documents)
    # Property documents should appear for a home loan.
    assert any("propert" in label.lower() for label in _labels(req))


def test_nre_account_additional_documents(kb):
    req = kb.requirements("nre_savings_account")
    all_docs = [d for g in req.groups for d in g.documents]
    assert any("passport" in d.lower() for d in all_docs)
    assert any("visa" in d.lower() or "residence permit" in d.lower() for d in all_docs)


def test_current_account_constitution(kb):
    req = kb.requirements("baroda_small_business_current_account", constitution="partnership_firm")
    assert any("partnership" in g.label.lower() for g in req.groups)
    docs = [d for g in req.groups for d in g.documents]
    assert any("partnership deed" in d.lower() for d in docs)


def test_minor_profile_adds_minor_extras(kb):
    req = kb.requirements("minor_savings_account", profile="minor")
    assert any("minor" in g.label.lower() for g in req.groups)


def test_unknown_product_raises(kb):
    import pytest

    with pytest.raises(KeyError):
        kb.requirements("not_a_real_product")


def test_no_core_kyc_string_leaks_into_docs(kb):
    # The literal "core_kyc (...)" reference items must be stripped.
    req = kb.requirements("nro_savings_account")
    for g in req.groups:
        for d in g.documents:
            assert not d.lower().lstrip().startswith("core_kyc")
