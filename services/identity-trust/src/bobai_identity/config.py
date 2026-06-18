"""Configuration for the Identity Trust engine. All values are env-driven."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Engine settings, loaded from environment / .env (prefix-free for shared keys)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Risk policy thresholds (0..1) ---
    threshold_step_up: float = 0.45
    threshold_deny: float = 0.85

    # --- Detector tunables ---
    # Implied travel speed (km/h) above which a location change is physically impossible.
    impossible_travel_kmh: float = 900.0
    # Below this many seconds between two distant events, geo-velocity is meaningless noise.
    min_travel_seconds: float = 60.0

    # --- Persistence ---
    db_path: str = "./data/identity_trust.db"

    # --- Privacy / integrity ---
    # Used to HMAC-tokenize PII and seed the tamper-evident audit hash chain.
    secret: str = "change-me-to-a-long-random-string"

    # --- WebAuthn / passkey step-up ---
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "BOBAI"
    webauthn_origin: str = "http://localhost:5173"

    # --- Optional IP geolocation enrichment ---
    geoip_mmdb_path: str | None = None


# Explicit env-var aliases so the shared .env (IDTRUST_*, WEBAUTHN_*) maps cleanly.
_ENV_ALIASES = {
    "threshold_step_up": "IDTRUST_THRESHOLD_STEP_UP",
    "threshold_deny": "IDTRUST_THRESHOLD_DENY",
    "impossible_travel_kmh": "IDTRUST_IMPOSSIBLE_TRAVEL_KMH",
    "db_path": "IDTRUST_DB_PATH",
    "secret": "IDTRUST_SECRET",
    "webauthn_rp_id": "WEBAUTHN_RP_ID",
    "webauthn_rp_name": "WEBAUTHN_RP_NAME",
    "webauthn_origin": "WEBAUTHN_ORIGIN",
    "geoip_mmdb_path": "GEOIP_MMDB_PATH",
}


@lru_cache
def get_settings() -> Settings:
    """Resolve settings, honouring the IDTRUST_*/WEBAUTHN_*/GEOIP_* env aliases."""
    import os

    overrides: dict[str, str] = {}
    for field, env_name in _ENV_ALIASES.items():
        value = os.getenv(env_name)
        if value is not None and value != "":
            overrides[field] = value
    return Settings(**overrides)
