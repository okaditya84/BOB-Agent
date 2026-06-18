# BOBAI — Pitch & Regulatory Alignment

**Problem statement (BoB × IIT Gandhinagar Hackathon 2026):** *Identity Trust,
Protection & Safety* — a privacy-first, risk-based Identity Trust framework that
continuously validates customer/enterprise identities across digital banking
channels, detects high-risk events, and triggers real-time step-up verification only
when risk is elevated, to reduce **account takeover (ATO), insider abuse, and KYC fraud**.

## How BOBAI answers it

| Requirement | BOBAI capability |
|---|---|
| Continuous identity validation | Every event scored by 5 detectors (geo-velocity, device, behavioral drift, context/network, ML anomaly) |
| Detect high-risk events | Impossible travel, new/untrusted device, behavioral change, off-hours, datacenter/Tor origin, anomalous combinations |
| Step-up **only** when elevated | Declarative policy: allow / monitor / **step-up** / deny — passkey/WebAuthn challenge fires only above threshold |
| Reduce ATO | Geo-velocity + device-trust + behavioral biometrics; high-risk events do **not** auto-trust new device/location |
| Reduce KYC fraud | Document tamper triage (ELA), OCR field cross-check, Aadhaar Verhoeff + PAN validation, provenance-first path |
| Reduce insider abuse | Privileged/recovery actions carry higher base sensitivity; tamper-evident hash-chained audit log |
| Privacy-first | PII stored only as HMAC tokens; browser-consent geolocation; data-minimising behavioral features |
| Enterprise/admin | Branded BOBAI platform: admins build & share agents, prompts, groups; attach MCP tools |

## Regulatory grounding (current as of 2026)

- **RBI (Authentication Mechanisms for Digital Payment Transactions) Directions, 2025**
  (issued 25 Sep 2025; compliance from 1 Apr 2026) — explicitly endorses **risk-based,
  factor-agnostic step-up** and alternatives to SMS-OTP. BOBAI's adaptive engine is a
  direct implementation.
- **NIST SP 800-63B-4** — risk tiers map to **AAL1/AAL2/AAL3**; passkeys/WebAuthn are
  the phishing-resistant authenticators used for step-up.
- **DPDP Act 2023** — privacy-first design: data minimisation, PII tokenisation,
  consent-based location, purpose limitation.
- **Provenance-first KYC** — DigiLocker / Aadhaar Offline e-KYC / Secure-QR signed
  artifacts are stronger than pixel forensics and need no AUA/KUA license to verify
  user-supplied signed documents.

## What's novel / defensible
1. **Explainability** — every decision carries ranked, plain-English reason codes
   (auditable; aligns with FCRA/ECOA-style "principal reasons" expectations).
2. **Tamper-evident audit** — hash-chained log; integrity is verifiable (`/v1/audit/verify`).
3. **Step-up, not friction-everywhere** — measured friction tied to real risk.
4. **Provider-agnostic & free/OSS** — `llm-rotate` + all-OSS detector stack
   (River, scikit-learn, py_webauthn, geoip2); no vendor lock-in, no paid SaaS.

## Built & verified
- 4 backend services (FastAPI) + branded BOBAI UI + MCP layer, all in Docker.
- **88 automated tests** green. Live demos: impossible-travel step-up, geo-enriched
  analytics dashboard, KYC checksum/fraud, grounded multilingual assistant.

## Honest scope (what we'd harden for production)
- WebAuthn step-up wired into the BOBAI login flow (engine + ceremony are built and
  tested; UI-login interception is the remaining integration).
- Liveness/anti-spoofing is print/replay-grade (OSS), not iBeta-certified.
- Cross-age face match is scoped to **adult re-verification** (not minor-to-adult).
- Risk thresholds shipped as sensible defaults; calibrate on real traffic to a target FAR.
