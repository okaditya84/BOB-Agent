"""Test fixtures — load the real BoB knowledge base from the repo data dir."""

from __future__ import annotations

from pathlib import Path

import pytest

from bobai_kyc.kb import KnowledgeBase

_KB_PATH = Path(__file__).resolve().parents[3] / "data" / "bob_documents_data.json"


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    return KnowledgeBase.from_file(_KB_PATH)
