from __future__ import annotations

import importlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pch_core.errors import NotFound, ValidationFailed
from pch_core.service import Hub

from pch_server.rest.auth import require_owner

SIM_DISABLED = "simulation disabled; set PCH_SIM_ENABLED=1 or pass --sim to pch serve"
SIM_LAB_MISSING = "simulation requires the pch-lab package (contributor tooling); use uv run pch-lab sim"


def require_sim(request: Request) -> None:
    if not getattr(request.app.state, "sim_enabled", False):
        raise HTTPException(status_code=404, detail=SIM_DISABLED)


router = APIRouter(tags=["sim"], dependencies=[Depends(require_sim)])


def _lab_sim(mod: str):
    """Load pch-lab sim modules only when a sim route runs. Not a package dependency."""
    try:
        return importlib.import_module(f"pch_lab.sim.{mod}")
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=SIM_LAB_MISSING) from exc


def _sim_hub(request: Request) -> Hub:
    existing = getattr(request.app.state, "sim_hub", None)
    if existing is not None:
        return existing
    sim_dir = getattr(request.app.state, "sim_dir", None)
    if sim_dir is None:
        raise HTTPException(status_code=404, detail=SIM_DISABLED)
    hub = Hub(Path(sim_dir), plain=True)
    request.app.state.sim_hub = hub
    return hub


@router.post("/sim/runs")
def start_run(
    request: Request,
    body: dict | None = None,
    _o: str = Depends(require_owner),
) -> dict:
    payload = body or {}
    target = str(payload.get("target") or "isolated")
    confirm = str(payload.get("confirm") or "")
    refuse = _lab_sim("refuse")
    if target == "everyday" and confirm != refuse.EVERYDAY_CONFIRM:
        raise ValidationFailed("everyday_unconfirmed")
    hub = request.app.state.hub if target == "everyday" else _sim_hub(request)
    try:
        session = _lab_sim("runner").start_threaded(
            hub,
            persona_id=str(payload.get("persona_id") or "lived-stretch"),
            delay_ms=int(payload.get("delay_ms") or 200),
            paired_assistant=bool(payload.get("paired_assistant")),
            auto_accept=payload.get("auto_accept", True) is not False,
            target=target,
        )
    except refuse.SimRefused as err:
        raise ValidationFailed(err.reason) from err
    request.app.state.sim_session = session
    return session.run


@router.get("/sim/runs")
def latest_run(request: Request, _o: str = Depends(require_owner)) -> dict:
    records = _lab_sim("records")
    session = getattr(request.app.state, "sim_session", None)
    if session is not None:
        return {**session.run, "ticks": _summaries(records.load_ticks(session.data_dir)[-20:])}
    run = records.load_run(_sim_hub(request).data_dir)
    if run is None:
        raise NotFound("no sim run")
    return {**run, "ticks": _summaries(records.load_ticks(_sim_hub(request).data_dir)[-20:])}


@router.get("/sim/runs/{run_id}")
def get_run(run_id: str, request: Request, _o: str = Depends(require_owner)) -> dict:
    data = latest_run(request, _o)
    if data.get("id") != run_id:
        raise NotFound("sim run")
    return data


@router.post("/sim/runs/{run_id}/pause")
def pause_run(run_id: str, request: Request, _o: str = Depends(require_owner)) -> dict:
    session = _session(request, run_id)
    session.pause()
    return session.run


@router.post("/sim/runs/{run_id}/resume")
def resume_run(run_id: str, request: Request, _o: str = Depends(require_owner)) -> dict:
    session = _session(request, run_id)
    session.resume()
    return session.run


@router.post("/sim/runs/{run_id}/stop")
def stop_run(run_id: str, request: Request, _o: str = Depends(require_owner)) -> dict:
    session = _session(request, run_id)
    session.stop()
    return session.run


@router.get("/sim/runs/{run_id}/ticks")
def list_ticks(run_id: str, request: Request, _o: str = Depends(require_owner)) -> list:
    directory = _run_dir(request, run_id)
    return _lab_sim("records").load_ticks(directory)


@router.get("/sim/runs/{run_id}/ticks/{seq}")
def get_tick(run_id: str, seq: int, request: Request, _o: str = Depends(require_owner)) -> dict:
    for tick in list_ticks(run_id, request, _o):
        if int(tick["seq"]) == seq:
            return tick
    raise NotFound("tick")


@router.get("/sim/objects/{obj_id}")
def get_object(obj_id: str, request: Request, _o: str = Depends(require_owner)) -> dict:
    return _sim_hub(request).get(obj_id)


def _session(request: Request, run_id: str):
    session = getattr(request.app.state, "sim_session", None)
    if session is None or session.run.get("id") != run_id:
        raise NotFound("sim run")
    return session


def _run_dir(request: Request, run_id: str):
    session = getattr(request.app.state, "sim_session", None)
    if session is not None and session.run.get("id") == run_id:
        return session.data_dir
    directory = _sim_hub(request).data_dir
    run = _lab_sim("records").load_run(directory)
    if run is None or run.get("id") != run_id:
        raise NotFound("sim run")
    return directory


def _summaries(ticks: list) -> list:
    out = []
    for tick in ticks:
        result = tick.get("result") or {}
        out.append(
            {
                "seq": tick.get("seq"),
                "simulated_at": tick.get("simulated_at"),
                "role": tick.get("role"),
                "action": tick.get("action"),
                "via": tick.get("via"),
                "status": tick.get("status"),
                "ok": result.get("ok"),
                "error": tick.get("error"),
            }
        )
    return out
