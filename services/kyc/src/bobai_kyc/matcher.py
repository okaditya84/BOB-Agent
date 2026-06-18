"""Check submitted documents against a RequirementSet.

Matching is fuzzy by necessity (documents are free-text descriptions), using
normalised token overlap — no document names are hardcoded; everything is derived
from the knowledge base and the user's submission.
"""

from __future__ import annotations

import re

from .schemas import CheckResult, GroupStatus, RequirementSet

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "of", "the", "a", "an", "for", "and", "or", "with", "in", "to", "on", "as",
    "any", "one", "not", "if", "is", "are", "your", "from", "via",
}
# Minimum token-overlap (relative to the shorter side) to call it a match.
_MATCH_THRESHOLD = 0.34


def _tokens(s: str) -> set[str]:
    return {t for t in _TOKEN.findall(s.lower()) if t not in _STOP and len(t) > 1}


def _matches(submitted_tokens: set[str], target: str) -> bool:
    tt = _tokens(target)
    if not tt or not submitted_tokens:
        return False
    common = submitted_tokens & tt
    if not common:
        return False
    return len(common) / min(len(submitted_tokens), len(tt)) >= _MATCH_THRESHOLD


def check(req: RequirementSet, submitted: list[str]) -> CheckResult:
    submitted_token_sets = [_tokens(s) for s in submitted]
    statuses: list[GroupStatus] = []
    required_units = 0
    satisfied_units = 0
    required_complete = True
    missing_summary: list[str] = []

    for g in req.groups:
        satisfied: list[str] = []
        missing: list[str] = []

        if g.pick_one:
            hit = next(
                (doc for doc in g.documents if any(_matches(s, doc) for s in submitted_token_sets)),
                None,
            )
            complete = hit is not None
            if hit:
                satisfied.append(hit)
            else:
                missing.append("any one of: " + ", ".join(g.documents))
            unit_total, unit_sat = 1, (1 if complete else 0)
        else:
            for doc in g.documents:
                if any(_matches(s, doc) for s in submitted_token_sets):
                    satisfied.append(doc)
                else:
                    missing.append(doc)
            complete = not missing
            unit_total, unit_sat = len(g.documents), len(satisfied)

        if g.required:
            required_units += unit_total
            satisfied_units += unit_sat
            if not complete:
                required_complete = False
                missing_summary.extend([g.label] if g.pick_one else missing)

        statuses.append(
            GroupStatus(
                label=g.label, required=g.required, pick_one=g.pick_one,
                satisfied=satisfied, missing=missing, complete=complete,
            )
        )

    completeness = (satisfied_units / required_units) if required_units else 1.0
    return CheckResult(
        product=req.product, profile=req.profile, constitution=req.constitution,
        groups=statuses, required_complete=required_complete,
        completeness=round(completeness, 3), missing_summary=missing_summary,
        notes=req.notes, disclaimer=req.disclaimer,
    )
