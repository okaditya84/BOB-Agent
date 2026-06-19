"""WebAuthn/passkey step-up routes."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bobai_identity.schemas import AuthEvent

router = APIRouter(prefix="/v1/webauthn", tags=["webauthn"])


class WebAuthnBegin(BaseModel):
    user_id: str


class WebAuthnComplete(BaseModel):
    user_id: str
    credential: dict[str, Any]
    # Optionally the event to promote to "trusted" once step-up succeeds.
    event: AuthEvent | None = None


@router.post("/register/begin")
def register_begin(body: WebAuthnBegin, request: Request) -> dict[str, Any]:
    try:
        return request.app.state.webauthn.registration_options(body.user_id, ts=time.time())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/register/complete")
def register_complete(body: WebAuthnComplete, request: Request) -> dict[str, Any]:
    try:
        return request.app.state.webauthn.verify_registration(body.user_id, body.credential)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/authenticate/begin")
def authenticate_begin(body: WebAuthnBegin, request: Request) -> dict[str, Any]:
    try:
        return request.app.state.webauthn.authentication_options(body.user_id, ts=time.time())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/authenticate/complete")
def authenticate_complete(body: WebAuthnComplete, request: Request) -> dict[str, Any]:
    try:
        result = request.app.state.webauthn.verify_authentication(body.user_id, body.credential)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # A verified step-up promotes the event's device/location to trusted.
    if result.get("verified") and body.event is not None:
        request.app.state.engine.trust_event(body.event)
    return result
