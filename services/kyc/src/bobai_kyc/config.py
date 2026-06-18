"""KYC service configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

def _default_kb_path() -> str:
    """Find the BoB KB by searching upward; robust to both local and container layouts.

    In containers the path is supplied via BOBAI_KYC_KB_PATH (this is only the default).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "bob_documents_data.json"
        if candidate.exists():
            return str(candidate)
    return "data/bob_documents_data.json"


_DEFAULT_KB = _default_kb_path()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOBAI_KYC_", env_file=".env", extra="ignore")

    # Path to the BoB document knowledge base (JSON).
    kb_path: str = str(_DEFAULT_KB)


@lru_cache
def get_settings() -> Settings:
    return Settings()
