"""Schemas for the KYC document-requirements API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Product(BaseModel):
    """A BoB product a customer can apply for."""

    id: str
    name: str
    category: str
    description: str = ""


class DocGroup(BaseModel):
    """A set of documents. `pick_one` means any single item satisfies the group."""

    label: str
    documents: list[str]
    required: bool = True  # False = conditional / situational
    pick_one: bool = False
    note: str | None = None


class RequirementSet(BaseModel):
    """The full document checklist for a product + applicant profile."""

    product: Product
    profile: str | None = None
    constitution: str | None = None
    groups: list[DocGroup]
    notes: list[str] = Field(default_factory=list)
    available_profiles: list[str] = Field(default_factory=list)
    disclaimer: str


class CheckRequest(BaseModel):
    product_id: str
    profile: str | None = None
    constitution: str | None = None
    submitted: list[str] = Field(default_factory=list)


class GroupStatus(BaseModel):
    label: str
    required: bool
    pick_one: bool
    satisfied: list[str]
    missing: list[str]
    complete: bool


class CheckResult(BaseModel):
    product: Product
    profile: str | None
    constitution: str | None
    groups: list[GroupStatus]
    required_complete: bool
    completeness: float = Field(ge=0, le=1)
    missing_summary: list[str]
    notes: list[str] = Field(default_factory=list)
    disclaimer: str


# --------------------------------------------------------------------------- #
#  Document onboarding-fraud schemas                                           #
# --------------------------------------------------------------------------- #
from enum import Enum  # noqa: E402


class DocumentType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    PASSPORT = "passport"
    VOTER_ID = "voter_id"
    DRIVING_LICENCE = "driving_licence"
    OTHER = "other"


class ClaimedFields(BaseModel):
    """What the applicant says is on the document — cross-checked against OCR."""

    name: str | None = None
    dob: str | None = None
    document_number: str | None = None


class ELAResult(BaseModel):
    """Error-Level-Analysis triage (best-effort on JPEGs; not forensic proof)."""

    score: float = Field(ge=0, le=1)
    mean_error: float
    max_error: float
    p95_error: float
    suspicious: bool
    note: str


class FieldCheck(BaseModel):
    field: str
    claimed: str | None
    extracted: str | None
    match: bool | None  # None = could not compare
    detail: str


class FraudVerdict(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    REJECT = "reject"


class FaceMatchResult(BaseModel):
    match: bool
    cosine: float | None
    faces_detected: dict[str, bool]
    threshold: float
    note: str
    disclaimer: str


class LivenessResult(BaseModel):
    live: bool
    score: float
    reason: str
    metrics: dict = Field(default_factory=dict)


class EkycVerifyResult(BaseModel):
    verified: bool
    liveness: LivenessResult
    face_match: FaceMatchResult
    summary: str
    disclaimer: str


class DocumentFraudReport(BaseModel):
    document_type: DocumentType
    ela: ELAResult
    extracted_fields: dict[str, str] = Field(default_factory=dict)
    format_valid: bool | None  # None = not applicable to this doc type
    format_detail: str
    field_checks: list[FieldCheck] = Field(default_factory=list)
    fraud_score: float = Field(ge=0, le=1)
    verdict: FraudVerdict
    flags: list[str] = Field(default_factory=list)
    ocr_used: bool
    disclaimer: str
