"""Assistant API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = Field(default_factory=list)
    language: str | None = None
    # Optional per-request override of provider/model (else env defaults).
    model: str | None = None
    provider: str | None = None


class Source(BaseModel):
    product_id: str | None
    title: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str
    provider: str
    grounded: bool
    usage: dict | None = None
    disclaimer: str


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    key_count: int
    default_model: str
    custom_endpoint: bool
