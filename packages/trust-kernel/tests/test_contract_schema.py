import pytest
from pch_core.schema.audit import EventKind
from pch_core.schema.contract import (
    ContextContract,
    ContextQuery,
    ContractItem,
    ItemRef,
    OmissionNote,
)
from pydantic import ValidationError


def test_empty_purpose_rejected():
    with pytest.raises(ValidationError):
        ContextQuery(purpose="")
    with pytest.raises(ValidationError):
        ContextQuery(purpose="   ")


def test_citation_required_on_item():
    ref = ItemRef(id="mem_1", type="memory", summary="x")
    with pytest.raises(ValidationError):
        ContractItem(
            ref=ref,
            body={"statement": "x"},
            citation=[],
            authority="user_confirmed",
            freshness="2026-08-26T00:00:00Z",
            untrusted=False,
        )


def test_omission_has_no_item_content_fields():
    note = OmissionNote(
        category="scope_not_granted", label="out-of-scope context withheld", count=2
    )
    dumped = note.model_dump()
    assert "id" not in dumped
    assert "title" not in dumped
    assert "ids" not in dumped
    assert set(dumped) == {"category", "label", "count"}
    with pytest.raises(ValidationError):
        OmissionNote(
            category="scope_not_granted",
            label="out-of-scope context withheld",
            count=2,
            title="hidden",
        )


def test_compiler_omission_categories_and_sufficient_default():
    off_task = OmissionNote(category="not_relevant", label="off-task context withheld", count=10)
    overflow = OmissionNote(category="over_cap", label="items over package size withheld", count=3)
    assert off_task.category == "not_relevant"
    assert overflow.category == "over_cap"
    assert ContextContract.model_fields["sufficient"].default is False


def test_context_contract_not_in_type_models():
    from pch_core.schema import TYPE_MODELS
    from pch_core.schema.metadata import EntityType

    assert ContextContract not in TYPE_MODELS.values()
    assert not hasattr(EntityType, "CONTEXT_CONTRACT")


def test_context_contract_event_kind():
    assert EventKind.CONTEXT_CONTRACT == "context.contract"
