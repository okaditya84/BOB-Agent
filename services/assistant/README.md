# BOBAI — Assistant

Multilingual, **grounded** document-guidance assistant over the BoB knowledge base
(`data/bob_documents_data.json`), provider-agnostic via **`llm-rotate`**.

## Run

```bash
uv sync --extra dev
# set at least one provider key, e.g.:
export OPENROUTER_API_KEY=...        # or OPENAI_/ANTHROPIC_/GOOGLE_/GROQ_/NVIDIA_API_KEY
export BOBAI_DEFAULT_PROVIDER=openrouter
export BOBAI_DEFAULT_MODEL=openai/gpt-4o-mini
uv run uvicorn bobai_assistant.main:app --reload --port 8003
uv run pytest
```

## Provider routing (llm-rotate)

The registry is built **dynamically from env**:
- Any provider whose key is set is wired up (OpenAI, Anthropic, Google, OpenRouter,
  and OpenAI-compatible **Groq** / **NVIDIA NIM** via custom `base_url`).
- **Multiple comma-separated keys** for one provider become rotatable credentials
  (`OPENAI_API_KEY=key1,key2`).
- A **cross-provider fallback chain** is configured for the default model.
- Switch provider/model with `BOBAI_DEFAULT_PROVIDER` / `BOBAI_DEFAULT_MODEL` — no code change.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/chat` | Grounded answer + sources (refuses to invent; replies in the user's language) |
| GET | `/v1/providers` | Which providers/keys are configured |
| GET | `/healthz` | Health + `llm_ready` |
