from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pch_core.service import Hub

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["projects"])


def _if_match(if_match: str | None) -> int | None:
    if not if_match:
        return None
    try:
        return int(if_match)
    except ValueError:
        return None


def _crud(name: str):
    @router.get(f"/{name}s" if not name.endswith("s") else f"/{name}")
    def _list(
        project: str | None = Query(default=None),
        hub: Hub = Depends(get_hub),
        _o: str = Depends(require_owner),
    ) -> list[dict]:
        return hub.list(name, project)

    return _list


@router.get("/projects")
def list_projects(project: str | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("project", project)


@router.post("/projects")
def create_project(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("project", body)


@router.get("/projects/{item_id}")
def get_project(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.get(item_id)


@router.patch("/projects/{item_id}")
def patch_project(item_id: str, body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner), if_match: str | None = Header(default=None, alias="If-Match")) -> dict:
    return hub.patch(item_id, body, _if_match(if_match))


@router.delete("/projects/{item_id}")
def delete_project(item_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.delete(item_id)


@router.get("/goals")
def list_goals(project: str | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("goal", project)


@router.post("/goals")
def create_goal(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("goal", body)


@router.get("/commitments")
def list_c(project: str | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("commitment", project)


@router.post("/commitments")
def create_c(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("commitment", body)


@router.get("/decisions")
def list_d(project: str | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.list("decision", project)


@router.post("/decisions")
def create_d(body: dict, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.create("decision", body)
