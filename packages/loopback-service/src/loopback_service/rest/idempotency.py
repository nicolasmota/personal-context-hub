from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from pch_core.service import Hub
from starlette.middleware.base import BaseHTTPMiddleware


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)
        key = request.headers.get("idempotency-key")
        if not key:
            return await call_next(request)
        hub: Hub = request.app.state.hub
        cached = hub.idempotency_get(key)
        if cached:
            status, body = cached
            return Response(content=body, status_code=status, media_type="application/json")
        response = await call_next(request)
        if 200 <= response.status_code < 300:
            raw = b""
            async for chunk in response.body_iterator:
                raw += chunk
            hub.idempotency_set(key, response.status_code, raw.decode())
            return Response(content=raw, status_code=response.status_code, media_type="application/json")
        return response
