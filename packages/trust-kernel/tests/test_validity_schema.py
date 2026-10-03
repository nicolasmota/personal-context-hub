import pytest
from pydantic import ValidationError
from trust_kernel.schema.contract import ContextQuery
from trust_kernel.schema.memory import Memory
from trust_kernel.schema.metadata import Authority, Classification, EntityType
from trust_kernel.schema.preference import Preference


def _pref(**extra):
    payload = {
        "id": "pref_1",
        "owner": "per_1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "type": EntityType.PREFERENCE,
        "key": "food.spicy",
        "value": "dislike",
        "classification": Classification.PERSONAL,
        "authority": Authority.USER_CONFIRMED,
    }
    payload.update(extra)
    return Preference(**payload)


def _mem(**extra):
    payload = {
        "id": "mem_1",
        "owner": "per_1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "type": EntityType.MEMORY,
        "statement": "I don't like spicy food",
        "classification": Classification.PERSONAL,
        "authority": Authority.USER_CONFIRMED,
    }
    payload.update(extra)
    return Memory(**payload)


def test_preference_interval_defaults():
    pref = _pref()
    assert pref.valid_from is None
    assert pref.valid_until is None
    assert pref.never_true is False


def test_memory_interval_defaults():
    mem = _mem()
    assert mem.valid_from is None
    assert mem.valid_until is None
    assert mem.never_true is False


def test_end_before_start_rejected():
    with pytest.raises(ValidationError):
        _pref(valid_from="2026-06-01T00:00:00Z", valid_until="2026-01-01T00:00:00Z")
    with pytest.raises(ValidationError):
        _mem(valid_from="2026-06-01T00:00:00Z", valid_until="2026-01-01T00:00:00Z")


def test_as_of_optional_and_invalid():
    q = ContextQuery(purpose="plan dinner")
    assert q.as_of is None
    q2 = ContextQuery(purpose="plan dinner", as_of="2026-01-01T00:00:00Z")
    assert q2.as_of == "2026-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        ContextQuery(purpose="plan dinner", as_of="not-a-timestamp")
