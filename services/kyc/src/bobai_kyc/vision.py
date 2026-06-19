"""Vision-LLM document classification via Groq (Llama 4 Scout).

Verifies an uploaded eKYC document is genuinely an identity document of the expected
type (not, e.g., a conference badge), and extracts the visible fields. Sends the image
as a base64 data URI to Groq's OpenAI-compatible chat completions endpoint.

The Groq key is read from GROQ_API_KEY; if absent the classifier reports
unavailable and the caller degrades gracefully (face-match still runs).
"""

from __future__ import annotations

import base64
import json
import os

import httpx

# Document types we recognise. "unknown" / "not_an_id" let us reject non-ID uploads.
ID_TYPES = {"aadhaar", "pan", "passport", "voter_id", "driving_licence"}

_SYSTEM = (
    "You are a strict KYC document classifier for an Indian bank. You are shown one image. "
    "Decide whether it is a genuine identity document and which type. Indian Aadhaar cards "
    "say 'Government of India' / show the Aadhaar logo and a 12-digit number (often 'XXXX XXXX XXXX'); "
    "PAN cards say 'INCOME TAX DEPARTMENT' with a 10-char PAN; passports, voter IDs and driving "
    "licences have their own marks. Conference badges, event passes, business/visiting cards, "
    "photos of people, screenshots, or random objects are NOT identity documents. "
    "Respond with ONLY a JSON object, no prose."
)

_USER = (
    "Classify this document. Return JSON exactly in this shape:\n"
    '{"is_identity_document": true|false, '
    '"document_type": "aadhaar|pan|passport|voter_id|driving_licence|other", '
    '"confidence": 0.0-1.0, '
    '"extracted": {"name": null|string, "dob": null|string, "document_number": null|string}, '
    '"reason": "short justification"}'
)


class DocumentVisionClassifier:
    def __init__(self, model: str, base_url: str, api_key: str | None = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("GROQ_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def classify(self, image_bytes: bytes, mime: str = "image/jpeg") -> dict:
        """Classify a document image. Returns a dict with availability + verdict."""
        if not self.available:
            return {"available": False, "reason": "GROQ_API_KEY not configured."}

        data_uri = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": _USER},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ]},
            ],
        }
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions", json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}, timeout=45.0,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, IndexError) as exc:
            return {"available": True, "ok": False, "reason": f"Vision call failed: {exc}"}

        dtype = str(parsed.get("document_type", "other")).lower()
        return {
            "available": True,
            "ok": True,
            "is_identity_document": bool(parsed.get("is_identity_document", False)),
            "document_type": dtype,
            "confidence": float(parsed.get("confidence", 0.0) or 0.0),
            "extracted": parsed.get("extracted", {}) or {},
            "reason": parsed.get("reason", ""),
        }
