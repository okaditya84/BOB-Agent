"""Assistant orchestrator: retrieve grounding context, then call the LLM."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from . import llm
from .prompts import DISCLAIMER, build_system_prompt
from .retriever import LexicalRetriever
from .schemas import ChatRequest, ChatResponse, Source

ChatFn = Callable[..., Awaitable[dict]]


class Assistant:
    def __init__(
        self,
        retriever: LexicalRetriever,
        default_provider: str,
        default_model: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        chat_fn: ChatFn | None = None,
        top_k: int = 5,
    ) -> None:
        self.retriever = retriever
        self.default_provider = default_provider
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.chat_fn = chat_fn or llm.chat
        self.top_k = top_k

    async def answer(self, req: ChatRequest) -> ChatResponse:
        hits = self.retriever.search(req.message, k=self.top_k)
        context = "\n\n".join(f"[{h.title}]\n{h.text}" for h in hits)
        sources = [Source(product_id=h.product_id, title=h.title, score=h.score) for h in hits]

        messages = [{"role": "system", "content": build_system_prompt(context, req.language)}]
        messages += [{"role": t.role, "content": t.content} for t in req.history]
        messages.append({"role": "user", "content": req.message})

        model = req.model or self.default_model
        provider = req.provider or self.default_provider
        result = await self.chat_fn(
            messages, model=model, provider=provider,
            temperature=self.temperature, max_tokens=self.max_tokens,
        )
        return ChatResponse(
            answer=result["content"],
            sources=sources,
            model=result.get("model") or model,
            provider=result.get("provider") or provider,
            grounded=bool(hits),
            usage=result.get("usage"),
            disclaimer=DISCLAIMER,
        )
