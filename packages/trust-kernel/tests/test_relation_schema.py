import pytest
from pch_core.errors import ValidationFailed, VersionConflict
from pch_core.schema.metadata import Authority, Classification, EntityType
from pch_core.schema.relation import Relation, RelationType
from pydantic import ValidationError


def _relation(**extra):
    payload = {
        "id": "rel_1",
        "owner": "per_1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "type": EntityType.RELATION,
        "from_id": "prj_a",
        "to_id": "prj_b",
        "relation_type": RelationType.DEPENDS_ON,
        "classification": Classification.PERSONAL,
        "authority": Authority.USER_CONFIRMED,
    }
    payload.update(extra)
    return Relation(**payload)


def test_four_relation_types():
    for value in ("owned_by", "depends_on", "blocked_by", "related_to"):
        _relation(relation_type=value)


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        _relation(relation_type="friends_with")


def test_self_link_rejected():
    with pytest.raises(ValidationError):
        _relation(from_id="prj_a", to_id="prj_a")


def test_duplicate_live_triple_conflict(hub):
    trip = hub.create("project", {"title": "Europe Trip", "status": "active"})
    visa = hub.create("project", {"title": "Visa renewal", "status": "active"})
    hub.create_relation(trip["id"], visa["id"], "depends_on")
    with pytest.raises(VersionConflict):
        hub.create_relation(trip["id"], visa["id"], "depends_on")


def test_self_link_create_is_422(hub):
    trip = hub.create("project", {"title": "Europe Trip", "status": "active"})
    with pytest.raises(ValidationFailed):
        hub.create_relation(trip["id"], trip["id"], "related_to")
