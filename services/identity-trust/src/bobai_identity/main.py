"""FastAPI app for the BOBAI Identity Trust engine."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .auth import WebAuthnService
from .config import get_settings
from .engine import RiskEngine
from .geoip import GeoIP
from .schemas import AuthEvent, RiskDecision
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


def _engine() -> RiskEngine:
    return app.state.engine


def _webauthn() -> WebAuthnService:
    return app.state.webauthn


# --------------------------------------------------------------------------- #
#  Requests                                                                    #
# --------------------------------------------------------------------------- #
class SignupRequest(BaseModel):
    password: str
    event: AuthEvent


class PasswordCheckRequest(BaseModel):
    password: str


class WebAuthnBegin(BaseModel):
    user_id: str


class WebAuthnComplete(BaseModel):
    user_id: str
    credential: dict[str, Any]
    # Optionally the event to promote to "trusted" once step-up succeeds.
    event: AuthEvent | None = None


# --------------------------------------------------------------------------- #
#  Health                                                                      #
# --------------------------------------------------------------------------- #
@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "identity-trust"}


# --------------------------------------------------------------------------- #
#  Core: risk evaluation                                                       #
# --------------------------------------------------------------------------- #
@app.post("/v1/risk/evaluate", response_model=RiskDecision)
def evaluate(event: AuthEvent) -> RiskDecision:
    return _engine().evaluate(event)


# --------------------------------------------------------------------------- #
#  Step-up: WebAuthn / passkeys                                                #
# --------------------------------------------------------------------------- #
@app.post("/v1/webauthn/register/begin")
def register_begin(body: WebAuthnBegin) -> dict[str, Any]:
    settings = app.state.settings
    try:
        return _webauthn().registration_options(body.user_id, ts=_now(settings))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/webauthn/register/complete")
def register_complete(body: WebAuthnComplete) -> dict[str, Any]:
    try:
        return _webauthn().verify_registration(body.user_id, body.credential)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/webauthn/authenticate/begin")
def authenticate_begin(body: WebAuthnBegin) -> dict[str, Any]:
    settings = app.state.settings
    try:
        return _webauthn().authentication_options(body.user_id, ts=_now(settings))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/webauthn/authenticate/complete")
def authenticate_complete(body: WebAuthnComplete) -> dict[str, Any]:
    try:
        result = _webauthn().verify_authentication(body.user_id, body.credential)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # A verified step-up promotes the event's device/location to trusted.
    if result.get("verified") and body.event is not None:
        _engine().trust_event(body.event)
    return result


# --------------------------------------------------------------------------- #
#  Observability: decisions + tamper-evident audit                            #
# --------------------------------------------------------------------------- #
@app.get("/v1/decisions")
def decisions(user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return app.state.store.recent_decisions(user_id=user_id, limit=limit)


@app.get("/v1/audit/verify")
def audit_verify() -> dict[str, Any]:
    return app.state.store.verify_audit_chain()


@app.get("/v1/analytics/summary")
def analytics_summary() -> dict[str, Any]:
    return app.state.store.analytics_summary()


@app.get("/v1/analytics/access")
def analytics_access(limit: int = 200) -> list[dict[str, Any]]:
    return app.state.store.access_recent(limit=limit)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


@app.get("/login", response_class=HTMLResponse)
def login_page() -> str:
    return (Path(__file__).parent / "login.html").read_text(encoding="utf-8")


@app.get("/signup", response_class=HTMLResponse)
def signup_page() -> str:
    return (Path(__file__).parent / "signup.html").read_text(encoding="utf-8")


@app.post("/v1/auth/password/check")
def password_check(body: PasswordCheckRequest) -> dict[str, Any]:
    from .auth import password

    return password.evaluate(body.password)


@app.post("/v1/auth/signup")
def signup(body: SignupRequest) -> dict[str, Any]:
    """New-customer signup: password-strength gate + signup-time risk assessment."""
    from .auth import password

    strength = password.evaluate(body.password)
    if not strength["acceptable"]:
        return {"created": False, "password": strength,
                "message": "Password too weak — please strengthen it."}

    # Force the event type to account_opening so the engine applies signup sensitivity.
    body.event.event_type = body.event.event_type.ACCOUNT_OPENING
    decision = _engine().evaluate(body.event)
    created = decision.action != decision.action.DENY
    return {
        "created": created,
        "password": strength,
        "risk": decision.model_dump(mode="json"),
        "recommend_passkey": decision.action.value in ("step_up", "monitor"),
        "message": "Account created. We recommend enrolling a passkey for stronger protection."
        if created else "Sign-up blocked: risk too high, please contact the branch.",
    }


@app.get("/v1/config")
def public_config() -> dict[str, Any]:
    """Non-secret config the login page needs (where to hand off after access)."""
    import os

    return {"bobai_ui_url": os.getenv("BOBAI_UI_URL", "http://localhost:3080")}


@app.get("/v1/users/{user_id}/profile")
def user_profile(user_id: str) -> dict[str, Any]:
    p = app.state.store.get_profile(user_id)
    # Return a non-PII summary (device tokens are HMACs, not raw fingerprints).
    return {
        "user_id": p.user_id,
        "event_count": p.event_count,
        "known_device_count": len(p.known_devices),
        "has_location_history": p.last_lat is not None,
        "has_behavioral_baseline": bool(p.behavioral_baseline),
    }


def _now(settings) -> float:
    """Server wall-clock for challenge timestamps (events carry their own time)."""
    import time

    return time.time()
