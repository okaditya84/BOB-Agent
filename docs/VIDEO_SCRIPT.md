# BOBAI — 5-Minute Video Walkthrough Script

Lead with the **security** story (the hackathon's actual problem: *Identity Trust,
Protection & Safety*), then show the assistant as the experience layer.

---

## ⚙️ PRE-RECORDING PREP (do this BEFORE you hit record — ~5 min)

1. **Start the system & seed demo data:**
   ```bash
   colima start
   cd "/Users/aditya/Documents/Aditya/Python/BOB Agent"
   make up && make seed
   ```
2. **Hard-refresh** http://localhost:3080 with **Cmd+Shift+R** (so the BOB-orange theme shows).
3. **Pre-create the admin + agent** (so you don't waste video time on setup):
   - Open http://localhost:3080 → Sign up → `BOB Admin` / `admin@bobai.local` / `BobAi@12345`.
   - Create an Agent named **BOB Help**, model OpenRouter `openai/gpt-4o-mini`, attach the
     **bobai** MCP tools (see `docs/WALKTHROUGH.md` step 3). Send it one test message.
4. **Have two files ready on your desktop** for eKYC: your **Aadhaar photo** and any
   **non-ID image** (e.g. a conference badge / random card).
5. **Open these tabs in order** (so you just switch tabs on camera):
   `:8001/` · `:8001/signup` · `:8001/login` · `:3080` · `:8002/ekyc` · `:8001/dashboard`
6. Have a Terminal window visible for the one step-up command.

---

## 🎬 THE SCRIPT (target 5:00)

### 0:00–0:25 · Hook + Portal  (tab: http://localhost:8001/)
> "This is **BOBAI** — a privacy-first, AI banking assistant for Bank of Baroda. Its core
> isn't just chat: it's an **Identity Trust engine** that continuously checks who's really
> there, and adds security friction *only* when risk is real."

Show the portal — point at the **For Customers** and **For Bank Staff / Admin** sections.

### 0:25–1:05 · Secure Signup  (tab: :8001/signup)
> "When a new customer signs up, we check password strength in real time and assess
> sign-up risk — device, location, network."

- Type a weak password → meter goes **red** ("very weak").
- Type a strong one → meter goes **green/orange**, ~100+ bits.
- Click **Create account** → show the **sign-up risk score** + "passkey recommended".
> "Passwords are stored only as **Argon2id hashes** — never plaintext."

### 1:05–2:00 · Risk-based Login + Step-up  (tab: :8001/login, then Terminal)
> "At login, we verify the password, then score the context."

- Sign in as your new user from your normal location → **Risk ~2% · LOW · allow** →
  click **→ Continue to BOBAI**.
> "Frictionless when it's really you. But watch what happens on an impossible login."

- Switch to **Terminal**, paste (one line):
  ```bash
  curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' -d '{"user_id":"attacker","event_type":"login","timestamp":1750000000,"device_fingerprint":"a","geo":{"lat":19.07,"lon":72.87}}' >/dev/null; curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' -d '{"user_id":"attacker","event_type":"login","timestamp":1750001200,"device_fingerprint":"b","geo":{"lat":35.68,"lon":139.69}}' | python3 -m json.tool
  ```
> "Mumbai, then Tokyo 20 minutes later on a new device — physically impossible. The engine
> returns **step_up**, demands a **phishing-resistant passkey** (NIST AAL2), and gives a
> plain-English reason. This is what stops account takeover."

Point at `"action": "step_up"`, the `reason_codes`, and `"required_aal": "AAL2"`.

### 2:00–2:50 · Live eKYC + AI document check  (tab: :8002/ekyc)
> "Onboarding fraud: we verify the *document* AND the *person*."

- **Start camera** → **Capture** your selfie.
- Upload the **non-ID image** (badge) → **Verify identity** →
  show **❌ Not verified — "not a valid identity document"** (AI vision caught it).
> "A vision AI confirms it's a genuine Aadhaar — a conference badge is rejected outright."

- Retake / re-upload your **real Aadhaar** → **Verify** →
  show **✅ Identity verified** — document type *aadhaar*, liveness pass, face match.
> "Genuine Aadhaar, live face, and a match across the age gap — verified."

### 2:50–3:50 · The Assistant (the original problem, fixed)  (tab: :3080)
> "The old bank bot couldn't even say what documents you need. BOBAI can — grounded in
> official Bank of Baroda rules, in any language."

- In **BOB Help** agent, type: `What documents do I need to open an NRE savings account?`
  → show it **calling the bobai MCP tools** and answering with a real checklist + sources.
- Then type: `hinglish me bata` → show the same answer in **Hinglish**.
> "Powered by any provider via llm-rotate, with web search and voice — and every answer
> is grounded, never hallucinated."

### 3:50–4:40 · Risk & Access Analytics  (tab: :8001/dashboard)
> "For the bank's security team — full visibility."

- Point at: the **risk-coloured map** of access locations, **step-up/deny rate**,
  the **Actions / Risk-band** bars, and **Recent events with 'why flagged'** reason codes.
> "Who accessed what, from where, what risk fired, and *why* — every decision explainable
> and written to a **tamper-evident, hash-chained audit log**."

### 4:40–5:00 · Close
> "BOBAI directly answers the hackathon brief — Identity Trust, Protection & Safety —
> aligned with the **RBI 2025 Authentication Directions**, **NIST 800-63B**, and the
> **DPDP Act**. Continuous identity trust, explainable decisions, friction only when risk
> is real. Thank you."

(Optionally end on the portal page.)

---

## TIPS
- Record at 1280×800+, browser zoom ~110% for readability.
- Practice once — the script is ~700 words ≈ 4.5 min spoken at a calm pace.
- If the passkey Touch-ID popup is awkward to film, the **terminal step_up JSON** is the
  reliable, clear way to prove step-up (already in the script).
- Keep each tab switch crisp; don't wait for slow typing — pre-type long questions.
