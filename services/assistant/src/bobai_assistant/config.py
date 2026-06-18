"""Assistant configuration — provider/model and service wiring, all env-driven."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/assistant/src/bobai_assistant/config.py -> parents[4] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_KB = _REPO_ROOT / "data" / "bob_documents_data.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOBAI_", env_file=".env", extra="ignore")

    # Provider + model are fully env-driven — switch with no code change.
    default_provider: str = "openrouter"   # BOBAI_DEFAULT_PROVIDER
    default_model: str = "openai/gpt-4o-mini"  # BOBAI_DEFAULT_MODEL
    kb_path: str = str(_DEFAULT_KB)         # BOBAI_KB_PATH
    kyc_service_url: str = "http://localhost:8002"  # BOBAI_KYC_SERVICE_URL
    temperature: float = 0.2
    max_tokens: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
