from __future__ import annotations

from fastapi import APIRouter, Depends
from pch_core.service import Hub

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["situation"])


@router.get("/situation")
def situation(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.current_situation()


@router.post("/situation/capture")
def capture_situation(
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    title = body.get("title")
    if title is not None:
        title = str(title)
    result = hub.owner_capture(str(body.get("statement") or ""), title=title)
    return {**result, "situation": hub.current_situation()}
