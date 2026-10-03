from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pch_core.service import Hub

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["memories"])


def _if_match(if_match: str | None) -> int | None:
    if not if_match:
        return None
    try:
        return int(if_match)
    except ValueError:
        return None


@router.get("/memories")
def list_mem(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list_truth("memory")


@router.post("/memories")
def create_mem(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("memory", body)


@router.get("/memories/{item_id}")
def get_mem(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.get(item_id, include_deleted=True)


@router.patch("/memories/{item_id}")
def patch_mem(
    item_id: str,
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict:
    return hub.patch(item_id, body, _if_match(if_match))


@router.post("/memories/{item_id}/supersede")
def supersede_mem(
    item_id: str,
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.supersede(item_id, body)


@router.post("/memories/{item_id}/retract")
def retract_mem(
    item_id: str,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.retract_never_true(item_id)


@router.delete("/memories/{item_id}")
def del_mem(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.delete(item_id)


@router.get("/artifacts")
def list_art(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("artifact")


@router.post("/artifacts")
def create_art(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("artifact", body)


@router.get("/preferences")
def list_pref(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list_truth("preference")


@router.post("/preferences")
def create_pref(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("preference", body)


@router.get("/preferences/{item_id}")
def get_pref(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.get(item_id, include_deleted=True)


@router.patch("/preferences/{item_id}")
def patch_pref(
    item_id: str,
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict:
    return hub.patch(item_id, body, _if_match(if_match))


@router.post("/preferences/{item_id}/supersede")
def supersede_pref(
    item_id: str,
    body: dict,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.supersede(item_id, body)


@router.post("/preferences/{item_id}/retract")
def retract_pref(
    item_id: str,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    return hub.retract_never_true(item_id)


@router.get("/profile")
def list_prof(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("profile")
