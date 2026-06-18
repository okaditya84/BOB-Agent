"""Retriever grounding tests against the real BoB KB."""

from __future__ import annotations

from pathlib import Path

import pytest

from bobai_assistant.retriever import LexicalRetriever

_KB = Path(__file__).resolve().parents[3] / "data" / "bob_documents_data.json"


@pytest.fixture(scope="session")
def retriever() -> LexicalRetriever:
    return LexicalRetriever.from_kb(_KB)


def test_nre_account_query_retrieves_nre(retriever):
    hits = retriever.search("what documents do I need to open an NRE account", k=5)
    ids = [h.product_id for h in hits]
    assert "nre_savings_account" in ids


def test_home_loan_query_retrieves_home_loan(retriever):
    hits = retriever.search("home loan documents for salaried", k=5)
    assert "home_loan" in [h.product_id for h in hits]


def test_core_kyc_is_indexed(retriever):
    titles = [c.title for c in retriever.chunks]
    assert "Core KYC documents" in titles


def test_empty_query_returns_nothing(retriever):
    assert retriever.search("   ", k=5) == []


def test_gold_loan_context_contains_real_docs(retriever):
    hits = retriever.search("gold loan", k=3)
    text = " ".join(h.text for h in hits).lower()
    assert "gold" in text and "ownership" in text
