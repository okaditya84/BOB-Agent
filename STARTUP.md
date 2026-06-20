# BOBAI — How to Turn the System On & Off

Copy-paste each block into Terminal, top to bottom.

## ▶ Turn ON

**1. Start Docker** (it sleeps after a Mac reboot):
```bash
colima start
```
*(If it says "already running", continue.)*

**2. Start all services:**
```bash
cd "/Users/aditya/Documents/Aditya/Python/BOB Agent"
make up
```
Wait until you see `BOBAI is up: …` (~30–60s; images are already built).

**3. (Optional) Load demo data for the dashboard:**
```bash
make seed
```

**4. Open in browser** (first time: hard-refresh chat with **Cmd+Shift+R** for the orange theme):

| What | URL |
|---|---|
| 🏠 BOBAI portal (start here) | http://localhost:8001/ |
| 💬 Chat assistant | http://localhost:3080 |
| 🔐 Secure login | http://localhost:8001/login |
| 🆕 Sign up | http://localhost:8001/signup |
| 🪪 Live eKYC | http://localhost:8002/ekyc |
| 📊 Risk dashboard | http://localhost:8001/dashboard |

---

## ⏹ Turn OFF
```bash
cd "/Users/aditya/Documents/Aditya/Python/BOB Agent"
make down
```

## 🔎 Check status
```bash
make ps          # what's running
make test        # run all 90 tests
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | `colima start` |
| Chat still looks blue (not orange) | Hard-refresh: **Cmd+Shift+R**, or open a private window |
| A page won't load | `make ps`; if a container is missing, `make up` again |
| Dashboard is empty | `make seed` |
| Chat says "no model" | In the chat, pick endpoint **OpenRouter** → model `openai/gpt-4o-mini` |
| Need full feature walkthrough | see `docs/WALKTHROUGH.md` |

First-ever run on a brand-new machine builds the branded LibreChat image (~15 min, one
time only). After that, `make up` just starts the containers.
