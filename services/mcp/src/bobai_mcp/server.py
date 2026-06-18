"""FastMCP server wrapping the BOBAI backend services as MCP tools.

Admins can attach this single MCP server in the BOBAI (LibreChat) UI and every
agent then gains document-guidance, KYC, and identity-risk capabilities. Tools
proxy to the REST services over HTTP, so the MCP layer stays thin.
"""

from __future__ import annotations

import os
import time

import httpx
from fastmcp import FastMCP

IDENTITY_URL = os.getenv("BOBAI_IDENTITY_URL", "http://localhost:8001").rstrip("/")
KYC_URL = os.getenv("BOBAI_KYC_URL", "http://localhost:8002").rstrip("/")
ASSISTANT_URL = os.getenv("BOBAI_ASSISTANT_URL", "http://localhost:8003").rstrip("/")
PORT = int(os.getenv("BOBAI_MCP_PORT", "8004"))

mcp = FastMCP("BOBAI")

_client: httpx.AsyncClient | None = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


@mcp.tool(
    description="List every Bank of Baroda product a customer can apply for "
    "(savings/current accounts, deposits, loans, PPF, NRI), with ids used by other tools."
)
async def list_bob_products() -> list[dict]:
    r = await _http().get(f"{KYC_URL}/v1/kyc/products")
    r.raise_for_status()
    return r.json()


@mcp.tool(
    description="Get the exact documents required to open/apply for a Bank of Baroda product. "
    "product_id comes from list_bob_products. profile is one of salaried/self_employed/nri/"
    "senior_citizen/minor/pensioner (when relevant); constitution is for current accounts "
    "(sole_proprietorship/partnership_firm/private_or_public_limited_company/llp/huf/trust_society_association)."
)
async def bob_document_requirements(
    product_id: str, profile: str | None = None, constitution: str | None = None
) -> dict:
    params = {"product_id": product_id}
    if profile:
        params["profile"] = profile
    if constitution:
        params["constitution"] = constitution
    r = await _http().get(f"{KYC_URL}/v1/kyc/requirements", params=params)
    if r.status_code == 404:
        return {"error": f"Unknown product '{product_id}'. Call list_bob_products first."}
    r.raise_for_status()
    return r.json()


@mcp.tool(
    description="Check a customer's submitted documents against a product's requirements; "
    "returns which are satisfied, what's missing, and a completeness score."
)
async def check_submitted_documents(
    product_id: str,
    submitted: list[str],
    profile: str | None = None,
    constitution: str | None = None,
) -> dict:
    body = {"product_id": product_id, "submitted": submitted, "profile": profile, "constitution": constitution}
    r = await _http().post(f"{KYC_URL}/v1/kyc/check", json=body)
    if r.status_code == 404:
        return {"error": f"Unknown product '{product_id}'. Call list_bob_products first."}
    r.raise_for_status()
    return r.json()


@mcp.tool(
    description="Ask the grounded Bank of Baroda assistant a natural-language question about "
    "accounts, deposits, loans or documents. Returns an answer grounded in official BoB rules "
    "with sources; replies in the user's language."
)
async def ask_bob_assistant(question: str, language: str | None = None) -> dict:
    body = {"message": question, "language": language}
    r = await _http().post(f"{ASSISTANT_URL}/v1/chat", json=body)
    r.raise_for_status()
    data = r.json()
    return {"answer": data["answer"], "sources": data.get("sources", []), "grounded": data.get("grounded")}


@mcp.tool(
    description="Assess the identity-trust risk of a login/transaction event and get a decision "
    "(allow/monitor/step_up/deny) with explainable reason codes. Use for fraud / account-takeover "
    "checks. Provide geo lat/lon (with user consent) and a device fingerprint when available."
)
async def assess_identity_risk(
    user_id: str,
    event_type: str = "login",
    ip: str | None = None,
    device_fingerprint: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    amount: float | None = None,
) -> dict:
    event: dict = {"user_id": user_id, "event_type": event_type, "timestamp": time.time()}
    if ip:
        event["ip"] = ip
    if device_fingerprint:
        event["device_fingerprint"] = device_fingerprint
    if lat is not None and lon is not None:
        event["geo"] = {"lat": lat, "lon": lon}
    if amount is not None:
        event["amount"] = amount
    r = await _http().post(f"{IDENTITY_URL}/v1/risk/evaluate", json=event)
    r.raise_for_status()
    d = r.json()
    return {
        "action": d["action"], "band": d["band"], "risk_score": d["risk_score"],
        "required_aal": d["required_aal"], "reason_codes": d["reason_codes"],
        "policy_rationale": d["policy_rationale"],
    }


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=PORT, path="/mcp")


if __name__ == "__main__":
    main()
