from __future__ import annotations

from fastapi import Depends, Header, Request
from trust_kernel.errors import Revoked
from trust_kernel.service import Hub


def get_hub(request: Request) -> Hub:
    return request.app.state.hub


async def current_actor(
    request: Request,
    authorization: str | None = Header(default=None),
    hub: Hub = Depends(get_hub),
) -> tuple[str, bool]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        token = request.headers.get("x-pch-token")
    if not token:
        raise Revoked("missing token")
    return hub.actor_from_token(token)


def require_owner(actor: tuple[str, bool] = Depends(current_actor)) -> str:
    name, is_owner = actor
    if not is_owner:
        raise Revoked("owner token required")
    return name
