# BOBAI — Step-by-Step Walkthrough (blindly followable)

Everything below is copy-paste. Assumes the stack is up (`make up`).

---

## 0. Confirm the stack is running

```bash
cd "/Users/aditya/Documents/Aditya/Python/BOB Agent"
make ps          # all containers should show "Up"
make seed        # populate the risk dashboard with demo events
```

Open these to confirm (all should load):
- BOBAI chat:        http://localhost:3080
- Secure Access:     http://localhost:8001/login
- Risk dashboard:    http://localhost:8001/dashboard
- Live eKYC:         http://localhost:8002/ekyc

---

## 1. Create your admin account (first user = ADMIN)

1. Go to **http://localhost:3080**
2. Click **Sign up**.
3. Fill in:
   - Name: `BOB Admin`
   - Email: `admin@bobai.local`
   - Password: `BobAi@12345`  (then confirm it)
4. Click **Submit**. You're logged in. **The first registered user is automatically ADMIN.**

---

## 2. Pick a model so chat works

1. Top-left of the chat, click the **model/endpoint selector**.
2. Choose endpoint **OpenRouter** → model **`openai/gpt-4o-mini`**
   (or endpoint **Groq** → **`llama-3.3-70b-versatile`**).
3. Type "hello" and press enter to confirm the model replies.

---

## 3. Create the "BOBAI Assistant" agent with the MCP tools

> The `bobai` MCP server (5 tools) is **already registered** — you just attach it.

1. In the left sidebar, open **Agents** (the agents icon) → **Create / New Agent**
   (a.k.a. the Agent Builder panel on the right).
2. Fill in:
   - **Name:** `BOBAI Assistant`
   - **Description:** `Secure Bank of Baroda assistant: documents, KYC, and identity-risk checks.`
   - **Provider / Model:** OpenRouter → `openai/gpt-4o-mini`
   - **Instructions** (paste exactly):

```
You are BOBAI, Bank of Baroda's official assistant. Use the available tools to answer:
- For "what documents do I need" questions, call bob_document_requirements (first call
  list_bob_products if you need the product id).
- To check a customer's submitted documents, call check_submitted_documents.
- For general account/deposit/loan questions, call ask_bob_assistant.
- For fraud / login-risk / account-takeover questions, call assess_identity_risk.
Never invent documents, eligibility rules, or amounts. Reply in the user's language.
Always end with: "Please confirm at your home branch or bankofbaroda.in before final submission."
```

3. In the agent builder, find **Tools** / **Add Tools** (or the **MCP** section) →
   select the server **`bobai`** → enable its tools:
   `list_bob_products`, `bob_document_requirements`, `check_submitted_documents`,
   `ask_bob_assistant`, `assess_identity_risk`.
4. Click **Create** (save). Select **BOBAI Assistant** as the active agent in the chat.

---

## 4. Use it — copy-paste these into the chat

```
What documents do I need to open an NRE savings account?
```
```
I'm salaried and want a home loan. What documents are required?
```
```
मुझे गोल्ड लोन के लिए कौन से दस्तावेज़ चाहिए?
```
```
A customer is logging in from Tokyo 20 minutes after logging in from Mumbai on a new device. Assess the identity risk.
```
```
I have an Aadhaar and PAN. For a bob Super Savings Account, what am I still missing?
```

You should see the agent call the BOBAI tools and answer with grounded checklists /
a risk decision with reason codes.

---

## 5. Create & share a Prompt (prompt library)

1. Left sidebar → **Prompts** → **New Prompt**.
2. Fill in:
   - **Name:** `Account Opening Checklist`
   - **Prompt text** (paste):
```
List the exact Bank of Baroda documents required to open a {{account_type}} account
for a {{profile}} applicant. Use a clear checklist and mark any "pick any one" groups.
```
3. Save. (`{{account_type}}` and `{{profile}}` become fill-in fields when used.)
4. To **share**: open the prompt → **Share** → choose users / groups / everyone.

---

## 6. Create a Group and share the agent (admin)

1. Left sidebar / settings → **Admin** (visible because you're ADMIN) →
   **Groups** → **New Group**:
   - **Name:** `Branch Staff`
2. Add members (any other users you registered).
3. Go back to **Agents** → open **BOBAI Assistant** → **Share** →
   select group **Branch Staff** → role **Viewer** (or Editor) → save.
   Now everyone in that group sees and can use the agent.

---

## 7. Voice (speech-to-text)

1. In a chat, click the **microphone** icon in the message box.
2. Allow microphone access. Speak: *"What documents do I need for an education loan?"*
3. It transcribes via Groq Whisper and sends. (Text-to-speech uses the browser voice
   if enabled in Settings → Speech.)

---

## 8. The security surfaces (no login needed) — copy-paste

### Secure Access (risk-based step-up)
1. Open **http://localhost:8001/login**
2. Customer ID: `ravi.kumar`, any password → **Sign in securely**.
3. Allow location when asked. Low risk → "Continue to BOBAI".
4. To force a **step-up**: in a terminal, simulate impossible travel for the same user,
   then sign in again:
```bash
curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' \
  -d '{"user_id":"ravi.kumar","event_type":"login","timestamp":1750000000,"device_fingerprint":"x","geo":{"lat":19.07,"lon":72.87}}' >/dev/null
curl -s -X POST localhost:8001/v1/risk/evaluate -H 'content-type: application/json' \
  -d '{"user_id":"ravi.kumar","event_type":"login","timestamp":1750001200,"device_fingerprint":"y","geo":{"lat":35.68,"lon":139.69}}'
```
   The second call returns `step_up` — and the login page will trigger a **passkey** prompt.

### Risk analytics dashboard
- Open **http://localhost:8001/dashboard** (run `make seed` first to populate it).

### Live eKYC (webcam → ID → face match)
1. Open **http://localhost:8002/ekyc**
2. **Start camera** → **Capture** a selfie.
3. **Upload** a photo of an ID (any portrait photo works for the demo).
4. **Verify identity** → shows liveness + face-match result.

---

## 9. Quick API checks (prove the backend without the UI)

```bash
# Document requirements (NRE account)
curl -s "localhost:8002/v1/kyc/requirements?product_id=nre_savings_account" | python3 -m json.tool | head -30

# Grounded assistant answer
curl -s -X POST localhost:8003/v1/chat -H 'content-type: application/json' \
  -d '{"message":"documents for a personal loan, salaried"}' | python3 -m json.tool

# Which providers are live
curl -s localhost:8003/v1/providers | python3 -m json.tool
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Chat says no model / error | Pick an endpoint+model (Step 2). Check keys in `.env`. |
| Agent doesn't call tools | Re-open the agent, confirm the `bobai` MCP tools are enabled (Step 3.3). |
| `bobai` MCP not listed | `docker logs LibreChat 2>&1 | grep MCP` should show "5 tools". If not: `cd platform/librechat && docker-compose restart api`. |
| Dashboard empty | `make seed` |
| Passkey prompt fails | Use the same browser/device; the page auto-enrols a passkey on first step-up. |
| Ports busy / nothing loads | `make ps`; if down, `make up`. |
