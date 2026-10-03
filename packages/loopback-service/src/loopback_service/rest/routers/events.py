from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from trust_kernel.service import Hub

from loopback_service.rest.auth import get_hub, require_owner

router = APIRouter(tags=["events"])


@router.get("/events")
def events(
    kind: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> list[dict]:
    return hub.events(kind, actor)


@router.get("/events/verify")
def verify(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.verify_events()
