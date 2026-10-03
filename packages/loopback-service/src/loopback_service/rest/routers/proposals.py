from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pch_core.service import Hub

from pch_server.rest.auth import current_actor, get_hub, require_owner

router = APIRouter(tags=["proposals"])


@router.post("/memories/proposals")
def propose(
    body: dict,
    hub: Hub = Depends(get_hub),
    actor: tuple[str, bool] = Depends(current_actor),
) -> dict:
    name, is_owner = actor
    evidence = body.get("evidence_refs") or []
    memory = body.get("memory") or body
    return hub.propose_memory(memory, name if not is_owner else "owner", evidence)


@router.get("/memories/proposals")
def list_proposals(
    status: str | None = Query(default=None),
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> list[dict]:
    rows = hub.list("proposal")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows


@router.post("/memories/proposals/{proposal_id}/accept")
def accept(proposal_id: str, body: dict | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.decide_proposal(proposal_id, True, (body or {}).get("edits"))


@router.post("/memories/proposals/{proposal_id}/reject")
def reject(proposal_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.decide_proposal(proposal_id, False)


@router.get("/conflicts")
def conflicts(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("conflict")


@router.post("/conflicts/{conflict_id}/resolve")
def resolve(
    conflict_id: str, body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    return hub.resolve_conflict(conflict_id, body.get("status", "resolved_keep_existing"))
