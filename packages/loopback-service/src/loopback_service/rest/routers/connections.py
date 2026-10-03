from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pch_core.errors import Revoked, ValidationFailed
from pch_core.service import Hub
from pydantic import BaseModel

from pch_server.pairing.catalog import get_assistant, list_assistants, render_recipe
from pch_server.rest.auth import current_actor, get_hub, require_owner

router = APIRouter(tags=["connections"])


def request_base_url(request: Request) -> str:
    hostname = request.url.hostname or "127.0.0.1"
    scheme = request.url.scheme or "http"
    port = request.url.port
    if hostname in {"testserver", "test"}:
        return "http://127.0.0.1:8765"
    if port is None:
        return f"{scheme}://{hostname}"
    return f"{scheme}://{hostname}:{port}"


class PairBody(BaseModel):
    code: str
    runtime_info: dict = {}


class GrantBody(BaseModel):
    connection_id: str
    preset: str | None = None
    capabilities: list[str] | None = None
    selectors: dict[str, str] | None = None
    classification_ceiling: str = "private"


class ManifestBody(BaseModel):
    purpose: str
    requested_capabilities: list[str]
    selectors: dict[str, str] = {}
    ttl_seconds: int = 900


class LinkBody(BaseModel):
    name: str = "agent"


class RecipeBody(BaseModel):
    assistant: str


@router.get("/catalog/assistants")
def catalog_assistants(_o: str = Depends(require_owner)) -> list[dict]:
    return list_assistants()


@router.post("/connections/{conn_id}/recipe")
def connection_recipe(
    conn_id: str,
    body: RecipeBody,
    request: Request,
    hub: Hub = Depends(get_hub),
    _o: str = Depends(require_owner),
) -> dict:
    entry = get_assistant(body.assistant)
    if not entry or not entry.get("supported"):
        raise ValidationFailed("unknown or unsupported assistant")
    hub.store.get(conn_id)
    token = hub.issue_connection_token(conn_id)
    recipe = render_recipe(body.assistant, token, request_base_url(request))
    hub.recipe_issued(conn_id, body.assistant)
    return recipe


@router.post("/connections/links")
def mint_link(
    body: LinkBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    return hub.mint_link(body.name)


@router.post("/connections/pair")
def pair(body: PairBody, hub: Hub = Depends(get_hub)) -> dict:
    return hub.pair(body.code, body.runtime_info)


@router.get("/connections")
def connections(hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> list[dict]:
    return hub.connections()


@router.post("/connections/{conn_id}/revoke")
def revoke(conn_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.revoke_connection(conn_id)


@router.post("/grants")
def create_grant(
    body: GrantBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    return hub.create_grant(
        body.connection_id,
        body.preset,
        body.capabilities,
        body.selectors,
        body.classification_ceiling,
    )


@router.post("/grants/{grant_id}/revoke")
def revoke_grant(
    grant_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    return hub.revoke_grant(grant_id)


@router.get("/grants")
def list_grants(
    connection: str | None = None, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> list[dict]:
    return hub.all_grants(connection)


@router.post("/context-manifests")
def create_manifest(
    body: ManifestBody,
    hub: Hub = Depends(get_hub),
    actor: tuple[str, bool] = Depends(current_actor),
) -> dict:
    name, is_owner = actor
    if is_owner:
        from pch_core.errors import ValidationFailed

        raise ValidationFailed("use CRUD as owner")
    return hub.create_manifest(
        name, body.purpose, body.requested_capabilities, body.selectors, body.ttl_seconds
    )


@router.get("/context-manifests/{manifest_id}")
def get_manifest(
    manifest_id: str,
    hub: Hub = Depends(get_hub),
    actor: tuple[str, bool] = Depends(current_actor),
) -> dict:
    name, is_owner = actor
    try:
        return hub.get_manifest(manifest_id, "owner" if is_owner else name)
    except Revoked:
        from fastapi import HTTPException

        raise HTTPException(status_code=410, detail="gone") from None
