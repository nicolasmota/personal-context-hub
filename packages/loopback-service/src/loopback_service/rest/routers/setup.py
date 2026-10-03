from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from trust_kernel.errors import Revoked
from trust_kernel.service import Hub

from loopback_service.rest.auth import get_hub, require_owner

router = APIRouter(tags=["setup"])


@router.post("/setup")
def setup(
    body: dict | None = None,
    hub: Hub = Depends(get_hub),
    authorization: str | None = Header(default=None),
) -> dict:
    payload = body or {}
    status = hub.setup_status()
    if status["initialized"] and not payload.get("restart"):
        if not authorization:
            raise Revoked("already initialized")
        actor, is_owner = hub.actor_from_token(authorization.split(" ", 1)[-1])
        if not is_owner:
            raise Revoked()
    result = hub.setup(payload.get("name", "Me"), restart=bool(payload.get("restart")))
    return {key: value for key, value in result.items() if key != "owner_token"}


@router.get("/setup")
def setup_status(hub: Hub = Depends(get_hub)) -> dict:
    return hub.setup_status()


@router.get("/spaces")
def spaces(_owner: str = Depends(require_owner)) -> list[dict]:
    return [{"id": "personal", "kind": "personal"}]


@router.get("/bootstrap")
def bootstrap(request: Request, hub: Hub = Depends(get_hub)) -> dict:
    """Loopback status only. The owner credential is a mode-0600 file, not this body."""
    return {
        "setup": hub.setup_status(),
        "sim_enabled": bool(getattr(request.app.state, "sim_enabled", False)),
        "owner_credential": "owner.token",
    }
