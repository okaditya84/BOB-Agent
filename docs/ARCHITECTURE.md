# BOBAI — Architecture

BOBAI is a secure, multilingual Bank of Baroda assistant whose **core is a
privacy-first, risk-based Identity Trust engine**. Every interaction is continuously
scored; step-up verification fires **only when risk is elevated**.

## Services

| Service | Port | Role |
|---|---|---|
| **identity-trust** | 8001 | Risk scoring, WebAuthn step-up, tamper-evident audit, **analytics dashboard** (`/dashboard`) |
| **kyc** | 8002 | Document-requirements resolver + onboarding-fraud (tamper/OCR/validators) |
| **assistant** | 8003 | Grounded RAG over the BoB KB, provider-agnostic via `llm-rotate` |
| **mcp** | 8004 | FastMCP server exposing the above as 5 MCP tools |
| **BOBAI UI** | 3080 | Branded LibreChat — agents, prompts, groups, sharing, voice, web search |
| infra | — | MongoDB, Meilisearch, pgvector, RAG-API (LibreChat) |

## How it fits together

```
            ┌─────────────── BOBAI UI (branded LibreChat) ───────────────┐
 user ───▶  │  chat · agents · prompts · groups · voice (Groq Whisper)   │
            │  providers via llm-rotate-style config (OpenRouter/Groq/    │
            │  Gemini) · web search (Tavily/Serper)                       │
            └───────────────┬───────────────────────────────┬───────────┘
                            │ MCP (streamable-http)          │ OpenAPI Actions
                            ▼                                ▼
                    ┌─────────────┐   tools    ┌───────────────────────────┐
                    │   mcp:8004  │──────────▶ │ identity-trust · kyc ·     │
                    └─────────────┘            │ assistant (FastAPI)        │
                                               └───────────────────────────┘
                                                  │            │          │
                                              SQLite       BoB KB      llm-rotate
                                          (risk+audit+    (JSON)     (any provider)
                                           access log)
```

- **Identity Trust** detectors: impossible-travel (geo-velocity), new-device,
  behavioral-biometric drift, contextual/network risk, and an ML anomaly model
  (River streaming + scikit IsolationForest) → blended, explainable score →
  policy (allow/monitor/step-up/deny) mapped to NIST AAL.
- **Privacy-first**: IP/device stored only as HMAC tokens; audit log is hash-chained;
  geolocation is browser-consent first, IP-derived only as fallback.
- **Provider-agnostic**: `llm-rotate` rotates keys + falls back across providers;
  switch provider/model from env, no code change.

## Run

```bash
cp .env.example .env   # fill provider keys (Google/OpenRouter/Groq is enough)
make up                # starts backend + branded LibreChat
make test              # 88 tests across services
```

Ports: UI `:3080` · dashboard `:8001/dashboard` · services `:8001–8004`.
