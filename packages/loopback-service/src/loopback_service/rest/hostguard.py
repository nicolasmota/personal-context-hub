from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
LOOPBACK_MSG = "The Hub is not a public server; it binds loopback only."


def hostname_of(host_header: str) -> str:
    host = host_header.split(",")[0].strip()
    if host.startswith("["):
        end = host.find("]")
        return host[1:end].lower() if end != -1 else host.lower()
    if host.count(":") == 1:
        host = host.rsplit(":", 1)[0]
    return host.lower()


async def reject_non_loopback_host(request: Request, call_next):
    host = hostname_of(request.headers.get("host", ""))
    if host not in LOOPBACK_HOSTS:
        return JSONResponse({"detail": LOOPBACK_MSG}, status_code=421)
    return await call_next(request)
