"""Orchestrator + API tests using an injected fake LLM (no real provider calls)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bobai_assistant.assistant import Assistant
from bobai_assistant.retriever import LexicalRetriever
from bobai_assistant.schemas import ChatRequest

_KB = Path(__file__).resolve().parents[3] / "data" / "bob_documents_data.json"


class FakeLLM:
    def __init__(self):
        self.last_messages = None

    async def __call__(self, messages, *, model, provider, temperature=0.2, max_tokens=1024):
        self.last_messages = messages
        return {"content": "Here is your checklist.", "model": model,
                "provider": provider, "usage": {"total_tokens": 42}}


async def test_answer_is_grounded_and_passes_context():
    fake = FakeLLM()
    assistant = Assistant(
        LexicalRetriever.from_kb(_KB), "openrouter", "openai/gpt-4o-mini", chat_fn=fake
    )
    resp = await assistant.answer(ChatRequest(message="documents to open an NRE account"))
    assert resp.grounded is True
    assert resp.sources
    assert resp.answer == "Here is your checklist."
    # The system prompt must carry the retrieved context (NRE needs a passport).
    system = fake.last_messages[0]
    assert system["role"] == "system"
    assert "passport" in system["content"].lower()


async def test_history_is_forwarded():
    fake = FakeLLM()
    assistant = Assistant(LexicalRetriever.from_kb(_KB), "openrouter", "m", chat_fn=fake)
    await assistant.answer(
        ChatRequest(
            message="and for a minor?",
            history=[{"role": "user", "content": "savings account docs?"},
                     {"role": "assistant", "content": "Here you go..."}],
        )
    )
    roles = [m["role"] for m in fake.last_messages]
    assert roles == ["system", "user", "assistant", "user"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key")
    from bobai_assistant import config

    config.get_settings.cache_clear()
    from bobai_assistant.main import app

    with TestClient(app) as c:
        # Replace the bound LLM with a fake so /v1/chat doesn't hit the network.
        c.app.state.assistant.chat_fn = FakeLLM()
        yield c
    config.get_settings.cache_clear()


def test_healthz_reports_llm_ready(client):
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["llm_ready"] is True


def test_providers_endpoint(client):
    data = client.get("/v1/providers").json()
    openrouter = next(p for p in data if p["name"] == "openrouter")
    assert openrouter["configured"] is True
    assert openrouter["key_count"] == 1


def test_chat_endpoint(client):
    r = client.post("/v1/chat", json={"message": "documents for a gold loan"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["sources"]
    assert body["disclaimer"]
