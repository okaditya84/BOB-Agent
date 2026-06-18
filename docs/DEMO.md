# BOBAI — Demo Script

Run `make up`, then follow these flows. Each maps directly to the hackathon problem
statement: **Identity Trust, Protection & Safety**.

## 0. Setup (once)
1. Open **http://localhost:3080** → register the first account (becomes **ADMIN**).
2. Create an **Agent** → under tools, attach the **`bobai`** MCP server.

---

## Flow 1 — Risk-based step-up (the headline)
Show that normal access is frictionless but anomalous access is challenged.

```bash
# Normal login from Mumbai — silent (allow)
curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' \
  -d '{"user_id":"ravi","event_type":"login","timestamp":1750000000,"device_fingerprint":"dA","geo":{"lat":19.07,"lon":72.87}}'

# 20 min later from Tokyo on a NEW device — impossible travel
curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' \
  -d '{"user_id":"ravi","event_type":"login","timestamp":1750001200,"device_fingerprint":"dB","geo":{"lat":35.68,"lon":139.69}}'
```
**Expected:** first → `allow`; second → `step_up` (band `high`) with reason
*"Impossible travel … exceeds plausible speed"* and `required_aal: AAL2`.
The step-up is a **phishing-resistant passkey (WebAuthn)**, not an SMS OTP.

## Flow 2 — Explainable analytics dashboard
Open **http://localhost:8001/dashboard**: risk-coloured map of access locations,
action/band charts, recent events with plain-English "why flagged", top risk reasons,
by-country. Re-run Flow 1 and watch it update (10s refresh).

## Flow 3 — KYC onboarding-fraud
```bash
# A forged Aadhaar number fails the Verhoeff checksum -> review/reject
curl -s -X POST localhost:8002/v1/kyc/document/analyze \
  -F file=@<aadhaar.jpg> -F document_type=aadhaar -F document_number=234123412340
```
**Expected:** `format_valid:false`, verdict `review/reject`, ELA tamper score, and any
claimed-vs-OCR field mismatches flagged.

## Flow 4 — The assistant fixes the original gap (in the branded UI)
In BOBAI chat, ask: **"What documents do I need to open an NRE savings account?"**
The agent calls the `bob_document_requirements` MCP tool and answers with the exact,
**grounded** checklist + sources — the thing the old bot couldn't do. Try it in Hindi
to show multilingual grounding.

## Flow 5 — Identity risk as an agent tool
Ask the agent: *"Assess login risk for user ravi from Tokyo, lat 35.68 lon 139.69."*
It calls `assess_identity_risk` and returns the decision + reason codes inside the chat.

---

## One-line story for judges
> BOBAI continuously validates identity across every banking interaction, explains
> every decision, and adds friction **only** when risk is real — reducing account
> takeover, insider abuse, and KYC fraud, with privacy and auditability built in.
