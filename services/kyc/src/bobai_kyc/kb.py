"""Knowledge base over bob_documents_data.json.

Turns the BoB document JSON into a uniform `RequirementSet` per product+profile.
A single generic walker handles the KB's varied shapes (account sub-types, loan
applicant profiles, current-account constitutions) so new products added to the
JSON are picked up without code changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import DocGroup, Product, RequirementSet

DISCLAIMER = (
    "Document/eligibility rules are revised periodically via RBI/BoB circulars. "
    "Confirm at your home branch or bankofbaroda.bank.in before final submission."
)

_META_KEYS = {"id", "name", "description", "category_label"}
_PROFILE_KEYS = {"applicant_profiles", "co_applicant_income_profiles"}
_INFO_KEYS = {"schemes_covered", "account_types"}
# Top-level KB keys that are not product categories.
_NON_CATEGORY_KEYS = {"meta", "core_kyc", "source_pages"}
_CONDITIONAL_HINTS = (
    "additional", "specific", "collateral", "property", "used_", "agri",
    "animal", "deemed", "if_needed", "minor", "above_",
)


def _prettify(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def _is_str_list(v) -> bool:
    return isinstance(v, list) and bool(v) and all(isinstance(x, str) for x in v)


def _is_conditional(key: str) -> bool:
    k = key.lower()
    return any(h in k for h in _CONDITIONAL_HINTS)


def _strip_core_refs(docs: list[str]) -> list[str]:
    """Drop items that merely re-reference core_kyc (we add the real core groups once)."""
    return [d for d in docs if not d.lower().lstrip().startswith("core_kyc")]


def _looks_like_product(d: dict) -> bool:
    """A dict is a product if it carries any document content or applicant profiles.

    Purely informational entries (e.g. an overview with only `account_types`) return
    False and are not listed as applyable products.
    """
    for key, val in d.items():
        if key in _PROFILE_KEYS and isinstance(val, dict) and val:
            return True
        if key in _META_KEYS or key in _INFO_KEYS:
            continue
        if _is_str_list(val) and ("document" in key.lower() or key.endswith("documents")):
            return True
    return False


@dataclass
class _Record:
    product: Product
    product_dict: dict
    category_common: list[str] | None
    category_constitution: dict | None


class KnowledgeBase:
    def __init__(self, raw: dict) -> None:
        self.raw = raw
        self._core = raw["core_kyc"]
        self._records: dict[str, _Record] = {}
        self._index()

    @classmethod
    def from_file(cls, path: str | Path) -> "KnowledgeBase":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    # ---- indexing (schema-driven, not keyed off hardcoded category names) ----
    def _index(self) -> None:
        for key, val in self.raw.items():
            if key in _NON_CATEGORY_KEYS or not isinstance(val, dict):
                continue
            label = val.get("category_label", _prettify(key))

            if "sub_types" in val and isinstance(val["sub_types"], list):
                # A category whose products are its sub-types (e.g. account variants).
                common = val.get("common_documents")
                constitution = val.get("additional_documents_by_constitution")
                for st in val["sub_types"]:
                    if not isinstance(st, dict) or "id" not in st:
                        continue
                    self._register(st["id"], st.get("name", _prettify(st["id"])), label,
                                   st.get("description", ""), st, common, constitution)
            else:
                # A container whose dict-children are individual products
                # (e.g. loans, other_products). Children that carry no document
                # content (purely informational) are skipped.
                for child_key, child in val.items():
                    if isinstance(child, dict) and _looks_like_product(child):
                        self._register(
                            child_key, child.get("category_label", _prettify(child_key)),
                            label, child.get("description", ""), child, None, None,
                        )

    def _register(self, pid, name, category, description, product_dict, common, constitution) -> None:
        self._records[pid] = _Record(
            product=Product(id=pid, name=name, category=category, description=description),
            product_dict=product_dict, category_common=common, category_constitution=constitution,
        )

    # ---- public API ----
    def list_products(self) -> list[Product]:
        return [r.product for r in self._records.values()]

    def has_product(self, product_id: str) -> bool:
        return product_id in self._records

    def requirements(
        self, product_id: str, profile: str | None = None, constitution: str | None = None
    ) -> RequirementSet:
        rec = self._records.get(product_id)
        if rec is None:
            raise KeyError(product_id)

        groups: list[DocGroup] = self._core_groups(profile)
        notes: list[str] = []

        if rec.category_common:
            docs = _strip_core_refs(rec.category_common)
            if docs:
                groups.append(DocGroup(label="Common documents", documents=docs, required=True))

        walked, wnotes, profiles_available = self._walk(rec.product_dict, profile, constitution)
        groups.extend(walked)
        notes.extend(wnotes)

        if rec.category_constitution and constitution and constitution in rec.category_constitution:
            docs = rec.category_constitution[constitution]
            if _is_str_list(docs):
                groups.append(
                    DocGroup(label=f"For {constitution.replace('_', ' ')}", documents=docs, required=True)
                )

        available_profiles = sorted(profiles_available)
        if rec.category_constitution and not available_profiles:
            available_profiles = sorted(rec.category_constitution.keys())
        if profile and available_profiles and profile not in available_profiles:
            notes.append(
                f"Profile '{profile}' not recognised for this product; "
                f"available: {', '.join(available_profiles)}."
            )

        return RequirementSet(
            product=rec.product, profile=profile, constitution=constitution,
            groups=groups, notes=notes, available_profiles=available_profiles,
            disclaimer=DISCLAIMER,
        )

    # ---- internals ----
    def _core_groups(self, profile: str | None) -> list[DocGroup]:
        c = self._core
        groups = [
            DocGroup(
                label="Identity & address proof (OVD)",
                documents=c["identity_and_address_ovd_pick_one"],
                pick_one=True, required=True, note="Pick any ONE",
            ),
            DocGroup(
                label="Tax ID", documents=c["mandatory_tax_id_pick_one"],
                pick_one=True, required=True, note="Pick any ONE (PAN or Form 60)",
            ),
            DocGroup(label="Universal extras", documents=c["universal_extras"], required=True),
            DocGroup(
                label="Current-address proof (only if your OVD lacks current address)",
                documents=c["deemed_ovd_for_current_address_if_needed_pick_one"],
                pick_one=True, required=False, note="Conditional",
            ),
        ]
        if profile == "minor" and c.get("minor_extras"):
            groups.append(DocGroup(label="Minor extras", documents=c["minor_extras"], required=True))
        return groups

    def _walk(
        self, d: dict, profile: str | None, constitution: str | None
    ) -> tuple[list[DocGroup], list[str], set[str]]:
        groups: list[DocGroup] = []
        notes: list[str] = []
        profiles_available: set[str] = set()

        for key, val in d.items():
            if key in _META_KEYS or key == "common_documents":
                # common_documents handled by caller (category_common) when relevant;
                # for loans it lives in product_dict, so handle it here too:
                if key == "common_documents" and _is_str_list(val):
                    docs = _strip_core_refs(val)
                    if docs:
                        groups.append(DocGroup(label="Common documents", documents=docs, required=True))
                continue

            if key in _PROFILE_KEYS and isinstance(val, dict):
                for pk, docs in val.items():
                    profiles_available.add(pk)
                    if profile is not None and pk == profile and _is_str_list(docs):
                        groups.append(
                            DocGroup(label=f"For {pk.replace('_', ' ')} applicants",
                                     documents=docs, required=True)
                        )
                continue

            if key == "additional_documents_by_constitution" and isinstance(val, dict):
                for ck, docs in val.items():
                    if constitution is not None and ck == constitution and _is_str_list(docs):
                        groups.append(
                            DocGroup(label=f"For {ck.replace('_', ' ')}", documents=docs, required=True)
                        )
                continue

            if key.endswith("note") or key == "notes":
                if isinstance(val, str):
                    notes.append(val)
                continue

            if key in _INFO_KEYS and _is_str_list(val):
                notes.append(f"{_prettify(key)}: " + "; ".join(val))
                continue

            if _is_str_list(val):
                docs = _strip_core_refs(val)
                if not docs:
                    continue
                conditional = _is_conditional(key)
                groups.append(
                    DocGroup(
                        label=_prettify(key), documents=docs,
                        required=not conditional,
                        note="Conditional" if conditional else None,
                    )
                )

        return groups, notes, profiles_available
