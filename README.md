# BOBAI — Secure Identity-Trust Banking Assistant

> Submission for the **Bank of Baroda × IIT Gandhinagar Hackathon 2026** — problem statement
> **"Identity Trust, Protection & Safety"** (Cybersecurity & Fraud).

BOBAI is a multilingual, voice-capable banking assistant whose **core is a privacy-first,
risk-based Identity Trust engine**. Every interaction — login, chat, document upload,
account recovery — is continuously scored for risk; **step-up verification is triggered only
when risk is elevated**. The goal is to reduce **account takeover (ATO)**, **insider/privileged
abuse**, and **KYC fraud**, exactly as the hackathon brief requires.

## Architecture (4 layers)

| Layer | What | Tech |
|---|---|---|
| 1. Experience | Branded chat UI + admin agent-builder (agents, MCP, skills, prompts, groups, sharing), multilingual + voice | LibreChat (+ admin panel), Obot |
| 2. Model routing | Any provider / any model from env; key rotation + fallback | `llm-rotate` |
| 3. **Identity Trust engine** | Risk scoring → policy → step-up; ATO, insider-abuse & KYC-fraud detection; explainable reason codes; privacy-first | **FastAPI service (`services/identity-trust`)** |
| 4. Data / infra | Sessions, agents, RAG vectors, risk events, tamper-evident audit log, analytics | SQLite / Mongo / pgvector, Docker |

## Repository layout

```
services/
  identity-trust/     # Layer 3 — the hackathon-winning core (built first)
  assistant/          # Layer 2/3 — RAG document assistant over the BoB KB (Phase 3)
  kyc/                # KYC onboarding-fraud module (Phase 2)
platform/
  librechat/          # Branded LibreChat fork (Phase 4)
  obot/               # Obot MCP governance (Phase 5)
data/
  bob_documents_data.json          # BoB KYC/document knowledge base (RAG + KYC ground truth)
  BOB_Documentation_Reference.md
docs/                 # Architecture, demo script, regulatory mapping
```

## Regulatory framing (for the pitch)
- **RBI (Authentication Mechanisms for Digital Payment Transactions) Directions, 2025** — risk-based step-up auth, alternatives to SMS-OTP (compliance from 1 Apr 2026).
- **NIST SP 800-63B-4** — Authentication Assurance Levels (AAL1/2/3); phishing-resistant passkeys.
- **DPDP Act 2023** — privacy-first, data-minimization, consent.

## Run

```bash
cp .env.example .env     # fill provider keys (Google/OpenRouter/Groq is enough)
make up                  # backend services + branded BOBAI (LibreChat) stack
make test                # 88 tests across services
```

- **BOBAI UI:** http://localhost:3080  (register first account → ADMIN)
- **Risk analytics dashboard:** http://localhost:8001/dashboard

## Docs
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — services, data flow, ports
- [`docs/DEMO.md`](docs/DEMO.md) — scripted judge demo (step-up, dashboard, KYC, assistant)
- [`docs/PITCH.md`](docs/PITCH.md) — problem-statement alignment + RBI 2025 / NIST / DPDP

## Status
Built & verified: Identity Trust engine + analytics dashboard, KYC + document-fraud,
RAG assistant (llm-rotate), MCP server (5 tools), branded BOBAI UI. 88 tests green.
Remaining: WebAuthn login-flow hook, eKYC face-match, Obot governance. See the task list.
