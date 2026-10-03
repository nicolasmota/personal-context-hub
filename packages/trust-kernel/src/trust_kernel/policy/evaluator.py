from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from trust_kernel.policy.grants import grant_is_current
from trust_kernel.schema.grant import Capability, Grant
from trust_kernel.schema.metadata import Classification

CLASS_RANK = {
    Classification.PUBLIC: 0,
    Classification.PERSONAL: 1,
    Classification.PRIVATE: 2,
    Classification.SENSITIVE: 3,
    "public": 0,
    "personal": 1,
    "private": 2,
    "sensitive": 3,
}


class Decision(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyInput:
    actor: str
    is_owner: bool
    grants: list[Grant]
    resource_type: str
    resource_project: str | None
    classification: str
    capability: str
    purpose: str | None = None


@dataclass
class PolicyResult:
    decision: Decision
    reason: str
    redactions: list[str]


def evaluate(inp: PolicyInput) -> PolicyResult:
    if inp.is_owner:
        return PolicyResult(Decision.ALLOW, "owner", [])
    active = [g for g in inp.grants if grant_is_current(g, datetime.now(UTC))]
    if not active:
        return PolicyResult(Decision.DENY, "no active grants", [])
    needed = inp.capability
    matching = [
        g
        for g in active
        if needed in [str(c) for c in g.capabilities] or needed in list(g.capabilities)
    ]
    if not matching and needed:
        # also allow project.read to cover goals/decisions/commitments
        if needed in ("goal.read", "decision.read", "commitment.read"):
            matching = [
                g
                for g in active
                if Capability.PROJECT_READ in g.capabilities
                or "project.read" in [str(c) for c in g.capabilities]
            ]
    if not matching:
        return PolicyResult(Decision.DENY, f"missing capability {needed}", [])
    for grant in matching:
        selector_project = grant.selectors.get("project")
        if selector_project and inp.resource_project and selector_project != inp.resource_project:
            continue
        if selector_project and not inp.resource_project:
            continue
        ceiling = CLASS_RANK.get(grant.classification_ceiling, 2)
        actual = CLASS_RANK.get(inp.classification, 1)
        if actual > ceiling:
            return PolicyResult(
                Decision.REDACT,
                "above classification ceiling",
                [f"withheld {inp.resource_type} classified {inp.classification}"],
            )
        if grant.purpose_constraint and inp.purpose and grant.purpose_constraint not in inp.purpose:
            return PolicyResult(Decision.DENY, "purpose mismatch", [])
        return PolicyResult(Decision.ALLOW, "grant matched", [])
    return PolicyResult(Decision.DENY, "selector mismatch", [])
