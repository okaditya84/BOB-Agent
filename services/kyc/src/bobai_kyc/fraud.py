"""Document onboarding-fraud orchestrator.

Combines three independent signals into one explainable verdict:
  1. Image tamper triage (ELA),
  2. Document-number format/checksum validity (Aadhaar Verhoeff, PAN),
  3. Cross-check of OCR-extracted fields against the applicant's claimed fields.
"""

from __future__ import annotations

import re

from .forensics import ela_analyze
from .ocr import OCREngine, extract_fields
from .schemas import (
    ClaimedFields,
    DocumentFraudReport,
    DocumentType,
    FieldCheck,
    FraudVerdict,
)
from .validators import digits_only, validate_aadhaar, validate_pan

DISCLAIMER = (
    "Automated triage only — not a legal determination of authenticity. "
    "Verify via official UIDAI/issuer channels and branch review before onboarding."
)

# Fraud-score blend weights + verdict thresholds (algorithm parameters).
_W_ELA = 0.35
_W_FORMAT = 0.40
_W_MISMATCH = 0.25
_REJECT_AT = 0.6
_REVIEW_AT = 0.3


def _name_tokens(s: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z]", " ", s.lower()).split() if len(t) > 1}


def analyze_document(
    image_bytes: bytes,
    document_type: DocumentType,
    claimed: ClaimedFields,
    ocr_engine: OCREngine | None = None,
    ocr_text: str | None = None,
) -> DocumentFraudReport:
    ela = ela_analyze(image_bytes)
    flags: list[str] = []
    if ela.suspicious:
        flags.append(f"ELA flagged possible image tampering (score {ela.score}).")

    # ---- OCR (real text from engine, or injected text for callers/tests) ----
    raw_text: str | None = None
    ocr_used = False
    if ocr_text is not None:
        raw_text, ocr_used = ocr_text, True
    elif ocr_engine is not None:
        try:
            raw_text = ocr_engine.image_to_text(image_bytes)
            ocr_used = True
        except Exception as exc:  # noqa: BLE001
            flags.append(f"OCR unavailable ({exc}); relied on claimed fields only.")
    extracted = extract_fields(raw_text) if raw_text else {}

    # ---- format / checksum validity ----
    number = extracted.get(document_type.value) or claimed.document_number
    format_valid: bool | None = None
    format_detail = "No checksum/format rule for this document type."
    format_score = 0.0
    if document_type == DocumentType.AADHAAR and number:
        format_valid, format_detail = validate_aadhaar(number)
    elif document_type == DocumentType.PAN and number:
        format_valid, format_detail = validate_pan(number)
    if format_valid is False:
        flags.append(format_detail)
        format_score = 1.0

    # ---- cross-checks (claimed vs document) ----
    field_checks: list[FieldCheck] = []
    mismatch_score = 0.0

    extracted_number = extracted.get(document_type.value)
    if claimed.document_number and extracted_number:
        if document_type == DocumentType.AADHAAR:
            cn, en = digits_only(claimed.document_number), digits_only(extracted_number)
        else:
            cn, en = claimed.document_number.upper().strip(), extracted_number.upper().strip()
        match = cn == en
        field_checks.append(
            FieldCheck(
                field="document_number", claimed=claimed.document_number,
                extracted=extracted_number, match=match,
                detail="Matches document." if match else "Does NOT match the document.",
            )
        )
        if not match:
            mismatch_score = max(mismatch_score, 1.0)
            flags.append("Claimed document number does not match the number on the document.")

    if claimed.name and raw_text:
        ctoks, rtoks = _name_tokens(claimed.name), _name_tokens(raw_text)
        match = bool(ctoks) and len(ctoks & rtoks) >= max(1, len(ctoks) // 2)
        field_checks.append(
            FieldCheck(
                field="name", claimed=claimed.name, extracted=None, match=match,
                detail="Name found on document." if match else "Claimed name not found in document text.",
            )
        )
        if not match:
            mismatch_score = max(mismatch_score, 0.6)
            flags.append("Claimed name not found in document text.")

    if claimed.dob and extracted.get("dob"):
        match = digits_only(claimed.dob) == digits_only(extracted["dob"])
        field_checks.append(
            FieldCheck(
                field="dob", claimed=claimed.dob, extracted=extracted["dob"], match=match,
                detail="DOB matches." if match else "DOB does not match.",
            )
        )
        if not match:
            mismatch_score = max(mismatch_score, 0.6)
            flags.append("Claimed date of birth does not match the document.")

    fraud_score = min(
        1.0, _W_ELA * ela.score + _W_FORMAT * format_score + _W_MISMATCH * mismatch_score
    )
    if fraud_score >= _REJECT_AT:
        verdict = FraudVerdict.REJECT
    elif fraud_score >= _REVIEW_AT or format_valid is False:
        verdict = FraudVerdict.REVIEW
    else:
        verdict = FraudVerdict.PASS

    if not flags:
        flags.append("No fraud indicators detected by automated triage.")

    return DocumentFraudReport(
        document_type=document_type, ela=ela, extracted_fields=extracted,
        format_valid=format_valid, format_detail=format_detail, field_checks=field_checks,
        fraud_score=round(fraud_score, 3), verdict=verdict, flags=flags,
        ocr_used=ocr_used, disclaimer=DISCLAIMER,
    )
