from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from pch_core.errors import PclError, Revoked


def problem(code: str, detail: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": f"https://pch.local/errors/{code}",
            "title": code,
            "status": status,
            "detail": detail,
        },
        media_type="application/problem+json",
    )


async def pcl_error_handler(request: Request, exc: PclError) -> JSONResponse:
    if isinstance(exc, Revoked) and request.url.path.rstrip("/").endswith("get_context_contract"):
        hub = getattr(request.app.state, "hub", None)
        if hub is not None:
            purpose = ""
            try:
                body = await request.json()
                if isinstance(body, dict):
                    purpose = str(body.get("purpose") or "")
            except Exception:
                purpose = ""
            hub.record_contract_refusal("unknown", purpose)
    return problem(exc.code, exc.detail, exc.status)
