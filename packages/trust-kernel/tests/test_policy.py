from pch_core.policy.evaluator import PolicyInput, evaluate
from pch_core.schema.grant import Capability, Grant, GrantStatus


def test_owner_always_allowed():
    r = evaluate(PolicyInput("owner", True, [], "memory", None, "sensitive", "memory.retrieve"))
    assert r.decision.value == "allow"


def test_project_scope_blocks_other_project():
    g = Grant(
        id="grant_1",
        connection_id="con_1",
        capabilities=[Capability.MEMORY_RETRIEVE, Capability.PROJECT_READ],
        selectors={"project": "prj_a"},
        classification_ceiling="private",
        status=GrantStatus.ACTIVE,
    )
    r = evaluate(PolicyInput("con_1", False, [g], "memory", "prj_b", "personal", "memory.retrieve"))
    assert r.decision.value == "deny"
