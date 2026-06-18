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
