from pch_core.policy.evaluator import PolicyInput, evaluate
from pch_core.schema.grant import Capability, Grant, GrantStatus


def test_redaction_above_ceiling():
    g = Grant(
        id="g",
        connection_id="c",
        capabilities=[Capability.MEMORY_RETRIEVE],
        selectors={"project": "p1"},
        classification_ceiling="personal",
        status=GrantStatus.ACTIVE,
    )
    r = evaluate(PolicyInput("c", False, [g], "memory", "p1", "sensitive", "memory.retrieve"))
    assert r.decision.value == "redact"
    assert r.redactions
