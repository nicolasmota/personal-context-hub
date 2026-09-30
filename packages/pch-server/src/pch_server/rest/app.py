from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pch_core.errors import PclError
from pch_core.service import Hub

from pch_server.mcp.server import ToolHub
from pch_server.rest.auth import current_actor, get_hub
from pch_server.rest.errors import pcl_error_handler
from pch_server.rest.hostguard import reject_non_loopback_host
from pch_server.rest.idempotency import IdempotencyMiddleware
from pch_server.rest.routers import (
    briefs,
    connections,
    events,
    memories,
    portability,
    projects,
    proposals,
    relations,
    search,
    setup,
    sim,
    situation,
    versions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        session = getattr(app.state, "sim_session", None)
        if session is not None:
            session.stop()


def create_app(
    hub: Hub | None = None,
    data_dir: Path | None = None,
    sim_hub: Hub | None = None,
    sim_dir: Path | None = None,
    sim_enabled: bool | None = None,
    catalog_refresh: bool | None = None,
) -> FastAPI:
    hub = hub or Hub(
        data_dir or Path(os.environ.get("PCH_DATA_DIR") or Path.home() / ".pch"),
        plain=os.environ.get("PCH_PLAIN_SQLITE") == "1",
    )
    if sim_hub is not None:
        sim_enabled = True
    elif sim_enabled is None:
        sim_enabled = os.environ.get("PCH_SIM_ENABLED") == "1"
    if catalog_refresh is None:
        catalog_refresh = os.environ.get("PCH_CATALOG_REFRESH") == "1"

    resolved_sim_hub: Hub | None = None
    resolved_sim_dir: Path | None = None
    if sim_enabled:
        if sim_hub is not None:
            resolved_sim_hub = sim_hub
            resolved_sim_dir = sim_hub.data_dir
        else:
            resolved_sim_dir = sim_dir or Path(
                os.environ.get("PCH_SIM_DIR") or (hub.data_dir / "_sim")
            )
            resolved_sim_hub = None
    app = FastAPI(title="Personal Context Hub", version="0.2.0", lifespan=lifespan)
    app.state.hub = hub
    app.state.sim_enabled = bool(sim_enabled)
    app.state.catalog_refresh = bool(catalog_refresh)
    app.state.sim_hub = resolved_sim_hub
    app.state.sim_dir = resolved_sim_dir
    app.state.sim_session = None
    app.state.mcp = ToolHub(hub)
    app.add_exception_handler(PclError, pcl_error_handler)
    app.add_middleware(IdempotencyMiddleware)
    app.middleware("http")(reject_non_loopback_host)
    for router in (
        setup.router,
        search.router,
        briefs.router,
        connections.router,
        proposals.router,
        events.router,
        portability.router,
        versions.router,
        memories.router,
        projects.router,
        situation.router,
        relations.router,
        sim.router,
    ):
        app.include_router(router, prefix="/v1")

    @app.post("/v1/mcp/tools/{name}")
    def mcp_tool(
        name: str,
        body: dict | None = None,
        hub_dep: Hub = Depends(get_hub),
        actor: tuple[str, bool] = Depends(current_actor),
    ) -> dict:
        ident, is_owner = actor
        try:
            return app.state.mcp.call(name, "owner" if is_owner else ident, **(body or {}))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown tool {name}") from exc

    @app.get("/v1/mcp/resources")
    def mcp_resource(
        uri: str,
        actor: tuple[str, bool] = Depends(current_actor),
    ) -> dict:
        ident, is_owner = actor
        data = app.state.mcp.resource(uri, "owner" if is_owner else ident)
        return {"uri": uri, "contents": data}

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    return app


def dev_app() -> FastAPI:
    data_dir = Path(os.environ.get("PCH_DATA_DIR") or (Path.home() / ".pch"))
    sim_dir = Path(os.environ.get("PCH_SIM_DIR") or (Path.home() / ".pch-sim"))
    plain = os.environ.get("PCH_PLAIN_SQLITE") == "1"
    return create_app(
        Hub(data_dir, plain=plain),
        sim_dir=sim_dir,
        sim_enabled=os.environ.get("PCH_SIM_ENABLED") == "1",
        catalog_refresh=os.environ.get("PCH_CATALOG_REFRESH") == "1",
    )
