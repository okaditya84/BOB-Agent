"""KYC service configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/kyc/src/bobai_kyc/config.py -> parents[4] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_KB = _REPO_ROOT / "data" / "bob_documents_data.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOBAI_KYC_", env_file=".env", extra="ignore")

    # Path to the BoB document knowledge base (JSON).
    kb_path: str = str(_DEFAULT_KB)


@lru_cache
def get_settings() -> Settings:
    return Settings()
