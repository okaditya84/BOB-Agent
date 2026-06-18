# BOBAI — Identity Trust Engine

Privacy-first, risk-based continuous authentication. The hackathon core.

## Run

```bash
uv sync --extra dev
uv run uvicorn bobai_identity.main:app --reload --port 8001
uv run pytest          # tests
```

## What it does

Every event (`POST /v1/risk/evaluate`) is scored by independent detectors —
impossible-travel (geo-velocity), new-device, behavioral-biometric drift,
contextual/network risk, and an unsupervised ML anomaly model — then blended into
an explainable risk score. A declarative policy maps the score to **allow / monitor /
step-up / deny** and a NIST AAL level. Elevated risk triggers a phishing-resistant
**passkey/WebAuthn** step-up. Decisions are written to a **tamper-evident,
hash-chained audit log**; PII (IP, device fingerprint) is stored only as HMAC tokens.

## Key endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/risk/evaluate` | Score an event → `RiskDecision` |
| POST | `/v1/webauthn/register/{begin,complete}` | Enrol a passkey |
| POST | `/v1/webauthn/authenticate/{begin,complete}` | Step-up challenge |
| GET | `/v1/decisions` | Recent decisions (analytics) |
| GET | `/v1/audit/verify` | Verify the audit hash chain is intact |
