"""Shared test fixtures."""

from __future__ import annotations

import pytest

from bobai_identity.config import Settings
from bobai_identity.engine import RiskEngine
from bobai_identity.engine.detectors.anomaly import RiskModel
from bobai_identity.store import Store

# A fixed daytime UTC epoch (2023-11-14 ~12:13 UTC, hour 12 → not off-hours).
BASE_TS = 1_700_000_000.0
MUMBAI = {"lat": 19.0760, "lon": 72.8777}
TOKYO = {"lat": 35.6762, "lon": 139.6503}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        threshold_step_up=0.45,
        threshold_deny=0.85,
        impossible_travel_kmh=900.0,
        db_path=":memory:",
        secret="test-secret-please-change",
    )


@pytest.fixture
def engine(settings: Settings) -> RiskEngine:
    store = Store(":memory:", settings.secret)
    return RiskEngine(store, settings, model=RiskModel(seed=42))
