# LibreChat env (BOBAI) — reference only (NO secrets here)

The runtime `.env` lives at `platform/librechat/.env` (gitignored). It is generated
from the repo-root `.env` by mapping variable names:

| Root `.env` | LibreChat `.env` | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | `GOOGLE_KEY` | Gemini (built-in endpoint) |
| `OPENROUTER_API_KEY` | `OPENROUTER_KEY` | OpenRouter custom endpoint |
| `GROQ_API_KEY` | `GROQ_API_KEY` | Groq endpoint + Whisper STT |
| `TAVILY_API_KEY` | `TAVILY_API_KEY` | Web search + scraper |
| `SERPER_API_KEY` | `SERPER_API_KEY` | Web search provider |
| `JWT_SECRET`,`JWT_REFRESH_SECRET`,`CREDS_KEY`,`CREDS_IV`,`MEILI_MASTER_KEY` | same | LibreChat secrets (auto-generated) |

Branding: `APP_TITLE=BOBAI`, custom footer, `HELP_AND_FAQ_URL`, `ALLOW_REGISTRATION=true`.

`deploy/librechat/librechat.yaml` is the canonical config (mounted into the container).
