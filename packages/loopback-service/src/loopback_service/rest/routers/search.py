from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pch_core.service import Hub

from pch_server.rest.auth import current_actor, get_hub

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    q: str = "",
    type: str | None = Query(default=None),
    project: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    purpose: str | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    hub: Hub = Depends(get_hub),
    actor: tuple[str, bool] = Depends(current_actor),
) -> dict:
    name, is_owner = actor
    return hub.search(
        q,
        type_=type,
        project_id=project,
        classification=classification,
        actor="owner" if is_owner else name,
        purpose=purpose,
        starts_from=from_,
        starts_to=to,
    )
