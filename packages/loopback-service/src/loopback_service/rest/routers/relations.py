from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pch_core.errors import ValidationFailed
from pch_core.service import Hub

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["relations"])


@router.post("/relations")
def create_relation(
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    from_id = body.get("from_id")
    to_id = body.get("to_id")
    relation_type = body.get("relation_type")
    if not from_id or not to_id or not relation_type:
        raise ValidationFailed("from_id, to_id, and relation_type are required")
    return hub.create_relation(str(from_id), str(to_id), str(relation_type))


@router.get("/relations")
def list_relations(
    from_id: str | None = Query(default=None),
    object_id: str | None = Query(default=None),
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> list[dict]:
    return hub.list_relations(from_id=from_id, object_id=object_id)


@router.patch("/relations/{relation_id}")
def patch_relation(
    relation_id: str,
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    relation_type = body.get("relation_type")
    if not relation_type:
        raise ValidationFailed("relation_type is required")
    return hub.patch_relation_type(relation_id, str(relation_type))


@router.delete("/relations/{relation_id}")
def delete_relation(
    relation_id: str,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.delete_relation(relation_id)


@router.get("/relation-proposals")
def list_relation_proposals(
    status: str | None = Query(default=None),
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> list[dict]:
    return hub.list_relation_proposals(status)


@router.post("/relation-proposals/{proposal_id}/accept")
def accept_relation_proposal(
    proposal_id: str,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.decide_relation_proposal(proposal_id, True)


@router.post("/relation-proposals/{proposal_id}/reject")
def reject_relation_proposal(
    proposal_id: str,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.decide_relation_proposal(proposal_id, False)
