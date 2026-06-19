"""Observability, config, profile, and HTML surface routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["observability"])


@router.get("/v1/decisions")
def decisions(request: Request, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return request.app.state.store.recent_decisions(user_id=user_id, limit=limit)


@router.get("/v1/audit/verify")
def audit_verify(request: Request) -> dict[str, Any]:
    return request.app.state.store.verify_audit_chain()


@router.get("/v1/analytics/summary")
def analytics_summary(request: Request) -> dict[str, Any]:
    return request.app.state.store.analytics_summary()


@router.get("/v1/analytics/access")
def analytics_access(request: Request, limit: int = 200) -> list[dict[str, Any]]:
    return request.app.state.store.access_recent(limit=limit)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return (Path(__file__).resolve().parent.parent / "dashboard.html").read_text(encoding="utf-8")


@router.get("/v1/config")
def public_config() -> dict[str, Any]:
    """Non-secret config the pages need (URLs of the other BOBAI surfaces)."""
    return {
        "bobai_ui_url": os.getenv("BOBAI_UI_URL", "http://localhost:3080"),
        "ekyc_url": os.getenv("BOBAI_EKYC_URL", "http://localhost:8002/ekyc"),
        "dashboard_url": "/dashboard",
        "login_url": "/login",
        "signup_url": "/signup",
    }


@router.get("/", response_class=HTMLResponse)
def portal() -> str:
    return (Path(__file__).resolve().parent.parent / "portal.html").read_text(encoding="utf-8")


@router.get("/v1/users/{user_id}/profile")
def user_profile(user_id: str, request: Request) -> dict[str, Any]:
    p = request.app.state.store.get_profile(user_id)
    # Return a non-PII summary (device tokens are HMACs, not raw fingerprints).
    return {
        "user_id": p.user_id,
        "event_count": p.event_count,
        "known_device_count": len(p.known_devices),
        "has_location_history": p.last_lat is not None,
        "has_behavioral_baseline": bool(p.behavioral_baseline),
    }
