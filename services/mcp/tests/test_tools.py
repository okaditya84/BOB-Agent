"""Tests for the BOBAI MCP tools.

Uses FastMCP's in-memory Client (no network for the MCP transport) and respx to mock
the backend REST services, so we exercise the real tool logic deterministically.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from bobai_mcp.server import ASSISTANT_URL, IDENTITY_URL, KYC_URL, mcp


async def _call(tool: str, args: dict):
    async with Client(mcp) as c:
        res = await c.call_tool(tool, args)
        return res.data if hasattr(res, "data") else res


async def test_list_tools_registers_all_five():
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
    assert names == {
        "list_bob_products", "bob_document_requirements",
        "check_submitted_documents", "ask_bob_assistant", "assess_identity_risk",
    }


@respx.mock
async def test_list_bob_products():
    respx.get(f"{KYC_URL}/v1/kyc/products").mock(
        return_value=httpx.Response(200, json=[{"id": "home_loan", "name": "Home Loan"}])
    )
    data = await _call("list_bob_products", {})
    assert data[0]["id"] == "home_loan"


@respx.mock
async def test_document_requirements_unknown_product():
    respx.get(f"{KYC_URL}/v1/kyc/requirements").mock(return_value=httpx.Response(404))
    data = await _call("bob_document_requirements", {"product_id": "nope"})
    assert "error" in data


@respx.mock
async def test_assess_identity_risk_maps_fields():
    respx.post(f"{IDENTITY_URL}/v1/risk/evaluate").mock(
        return_value=httpx.Response(200, json={
            "action": "step_up", "band": "high", "risk_score": 0.7,
            "required_aal": "AAL2", "reason_codes": ["Impossible travel"],
            "policy_rationale": "elevated risk",
        })
    )
    data = await _call("assess_identity_risk",
                       {"user_id": "u1", "lat": 35.6, "lon": 139.7})
    assert data["action"] == "step_up"
    assert data["reason_codes"] == ["Impossible travel"]


@respx.mock
async def test_ask_bob_assistant_returns_grounded_answer():
    respx.post(f"{ASSISTANT_URL}/v1/chat").mock(
        return_value=httpx.Response(200, json={
            "answer": "You need a PAN and Aadhaar.",
            "sources": [{"title": "Core KYC"}], "grounded": True,
        })
    )
    data = await _call("ask_bob_assistant", {"question": "docs?"})
    assert data["grounded"] is True
    assert "PAN" in data["answer"]
