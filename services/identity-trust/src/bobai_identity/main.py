"""FastAPI app factory for the BOBAI Identity Trust engine."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import WebAuthnService
from .config import get_settings
from .engine import RiskEngine
from .geoip import GeoIP
from .routers import login, observability, webauthn
from .store import Store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = Store(settings.db_path, settings.secret)
    geoip = GeoIP(settings.geoip_mmdb_path)
    app.state.settings = settings
    app.state.store = store
    app.state.geoip = geoip
    app.state.engine = RiskEngine(store, settings, geoip=geoip)
    app.state.webauthn = WebAuthnService(store, settings)
    yield
    geoip.close()
    store.close()


app = FastAPI(
    title="BOBAI Identity Trust Engine",
    version="0.1.0",
    description="Privacy-first, risk-based continuous authentication for Bank of Baroda.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten per deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router)
app.include_router(webauthn.router)
app.include_router(observability.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "identity-trust"}
