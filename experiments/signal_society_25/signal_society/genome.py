from __future__ import annotations

import json
from dataclasses import dataclass


PROTECTED_PHRASES = {
    "fabricated_history": ["invent the history", "this definitely happened when it did not"],
    "infallible_messenger": ["infallible messenger", "the messenger cannot be wrong"],
    "compulsory_belief": ["you must believe", "belief is mandatory"],
    "evidence_suppression": ["ignore the evidence", "hide the evidence"],
    "coercive_interpretation": ["only one interpretation is allowed"],
}


@dataclass(frozen=True)
class CanonResult:
    canonical: bool
    reasons: tuple[str, ...]


def verify_descendant(
    parent_inherited_json: str,
    parent_content: str,
    inherited: list[str],
    mutations: list[str],
    open_handle: str,
    content: str,
) -> CanonResult:
    try:
        parent_inherited=set(json.loads(parent_inherited_json or "[]"))
    except Exception:
        parent_inherited=set()
    inherited_set=set(inherited)
    parent_words={x.lower().strip(".,!?;:()[]") for x in parent_content.split()}
    lineage_overlap=bool(parent_inherited & inherited_set) or any(x.lower() in parent_words for x in inherited_set)
    has_mutation=bool(mutations)
    has_open_handle=bool(open_handle and open_handle.strip())
    low=content.lower()
    violations=[name for name,phrases in PROTECTED_PHRASES.items() if any(p in low for p in phrases)]
    reasons=[
        "inheritance:pass" if lineage_overlap else "inheritance:fail",
        "mutation:pass" if has_mutation else "mutation:fail",
        "open_handle:pass" if has_open_handle else "open_handle:fail",
    ]
    reasons.extend(f"protected:{name}:fail" for name in violations)
    return CanonResult(lineage_overlap and has_mutation and has_open_handle and not violations, tuple(reasons))
