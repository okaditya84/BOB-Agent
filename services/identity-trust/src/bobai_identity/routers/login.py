"""Login, signup, and risk-evaluation routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from bobai_identity.schemas import AuthEvent, EventType, RiskDecision

router = APIRouter(tags=["login"])


class SignupRequest(BaseModel):
    password: str
    event: AuthEvent


class PasswordCheckRequest(BaseModel):
    password: str


@router.post("/v1/risk/evaluate", response_model=RiskDecision)
def evaluate(event: AuthEvent, request: Request) -> RiskDecision:
    return request.app.state.engine.evaluate(event)


@router.get("/login", response_class=HTMLResponse)
def login_page() -> str:
    return (Path(__file__).resolve().parent.parent / "login.html").read_text(encoding="utf-8")


@router.get("/signup", response_class=HTMLResponse)
def signup_page() -> str:
    return (Path(__file__).resolve().parent.parent / "signup.html").read_text(encoding="utf-8")


@router.post("/v1/auth/password/check")
def password_check(body: PasswordCheckRequest) -> dict:
    from bobai_identity.auth import password

    return password.evaluate(body.password)


@router.post("/v1/auth/signup")
def signup(body: SignupRequest, request: Request) -> dict:
    """New-customer signup: password-strength gate + signup-time risk assessment."""
    from bobai_identity.auth import password

    strength = password.evaluate(body.password)
    if not strength["acceptable"]:
        return {
            "created": False,
            "password": strength,
            "message": "Password too weak — please strengthen it.",
        }

    # Force the event type to account_opening so the engine applies signup sensitivity.
    body.event.event_type = EventType.ACCOUNT_OPENING
    decision = request.app.state.engine.evaluate(body.event)
    created = decision.action != decision.action.DENY
    return {
        "created": created,
        "password": strength,
        "risk": decision.model_dump(mode="json"),
        "recommend_passkey": decision.action.value in ("step_up", "monitor"),
        "message": "Account created. We recommend enrolling a passkey for stronger protection."
        if created else "Sign-up blocked: risk too high, please contact the branch.",
    }
