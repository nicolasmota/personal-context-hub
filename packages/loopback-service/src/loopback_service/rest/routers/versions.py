from __future__ import annotations

from fastapi import APIRouter, Depends
from pch_core.service import Hub

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["versions"])


@router.get("/memories/{item_id}/versions")
def mem_versions(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.versions(item_id)


@router.get("/projects/{item_id}/versions")
def proj_versions(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.versions(item_id)
