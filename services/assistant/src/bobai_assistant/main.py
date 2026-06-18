"""FastAPI app for the BOBAI assistant."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import llm
from .assistant import Assistant
from .config import get_settings
from .llm import PROVIDER_DEFS
from .retriever import LexicalRetriever
from .schemas import ChatRequest, ChatResponse, ProviderStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.retriever = LexicalRetriever.from_kb(s.kb_path)
    app.state.registry = llm.configure_llm(
        default_provider=s.default_provider, default_model=s.default_model
    )
    app.state.llm_ready = bool(app.state.registry.use_keys)
    app.state.assistant = Assistant(
        app.state.retriever, s.default_provider, s.default_model, s.temperature, s.max_tokens
    )
    yield


app = FastAPI(
    title="BOBAI Assistant",
    version="0.1.0",
    description="Multilingual, grounded BoB document-guidance assistant (provider-agnostic).",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "assistant", "llm_ready": app.state.llm_ready}


@app.get("/v1/providers", response_model=list[ProviderStatus])
def providers() -> list[ProviderStatus]:
    reg = app.state.registry
    return [
        ProviderStatus(
            name=name,
            configured=name in reg.configured,
            key_count=sum(1 for k in reg.keys if k["provider"] == d["provider"]),
            default_model=d["default_model"],
            custom_endpoint=d["custom"],
        )
        for name, d in PROVIDER_DEFS.items()
    ]


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not app.state.llm_ready:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider configured. Set a provider key "
            "(e.g. OPENROUTER_API_KEY / GROQ_API_KEY) in the environment.",
        )
    try:
        return await app.state.assistant.answer(req)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc
