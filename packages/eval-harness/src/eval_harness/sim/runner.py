from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pch_core.ids import new_id
from pch_core.service import OWNER, Hub
from pch_core.timeutil import now_iso

from pch_lab.sim.persona import QUERY_ACTIONS, compile_persona
from pch_lab.sim.records import load_run, save_run, save_ticks
from pch_lab.sim.refuse import EVERYDAY_CONFIRM, SimRefused

ASSISTANT_CAPS = [
    "project.read",
    "commitment.read",
    "memory.retrieve",
    "memory.propose",
    "profile.read",
]


def default_sim_dir() -> Path:
    return Path.home() / ".pch-sim"


def default_everyday_dir() -> Path:
    return Path.home() / ".pch"


def resolve_data_dir(
    *,
    data_dir: Path | None,
    target: str,
    confirm: str,
    everyday_dir: Path | None,
) -> Path:
    everyday = everyday_dir or default_everyday_dir()
    if target == "everyday":
        if confirm != EVERYDAY_CONFIRM:
            raise SimRefused("everyday_unconfirmed")
        return everyday
    if target != "isolated":
        raise SimRefused("unknown_target", target)
    return data_dir or default_sim_dir()


def situation_project_id(contract: dict[str, Any]) -> str | None:
    sit = contract.get("situation")
    if isinstance(sit, dict):
        return sit.get("project_id")
    if isinstance(sit, str):
        return sit
    return None


def cited_ids(contract: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("goals", "preferences", "memories", "decisions", "constraints", "state"):
        for item in contract.get(key) or []:
            ref = item.get("ref") if isinstance(item, dict) else None
            if isinstance(ref, dict) and ref.get("id"):
                ids.append(str(ref["id"]))
    return ids


def mint_assistant(hub: Hub, project_id: str | None = None) -> dict[str, Any]:
    link = hub.mint_link("sim-assistant", labels=["sim", "test-tooling"])
    paired = hub.pair(link["code"], runtime_info={"harness": "pch-lab-sim"})
    selectors = {"project": project_id} if project_id else None
    hub.create_grant(
        paired["connection_id"],
        None,
        ASSISTANT_CAPS,
        selectors,
        "private",
    )
    return paired


def _ensure_setup(hub: Hub) -> None:
    try:
        hub.person_id()
    except Exception:
        hub.setup("Sim")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expand_auto_accept(ticks: list[dict[str, Any]], auto_accept: bool) -> list[dict[str, Any]]:
    if not auto_accept:
        return [{**t, "seq": i} for i, t in enumerate(ticks, start=1)]
    out: list[dict[str, Any]] = []
    seq = 1
    for raw in ticks:
        tick = {**raw, "seq": seq}
        out.append(tick)
        seq += 1
        if raw["action"] == "propose_memory":
            out.append(
                {
                    "seq": seq,
                    "simulated_at": raw["simulated_at"],
                    "role": "owner",
                    "action": "decide_proposal",
                    "input": {"accept": True, "after_seq": tick["seq"]},
                    "via": raw.get("via", "in_process_pair"),
                    "status": "pending",
                    "result": None,
                    "error": None,
                }
            )
            seq += 1
    return out


def _object_count(hub: Hub) -> int:
    n = 0
    for type_ in ("project", "goal", "preference", "memory", "commitment", "decision"):
        n += len(hub.list(type_))
    return n


def _apply_create(
    hub: Hub, tick: dict[str, Any], keys: dict[str, str]
) -> dict[str, Any]:
    payload = tick["input"]
    body = dict(payload["body"])
    project_key = body.pop("project_key", None)
    if project_key:
        body["project_id"] = keys[project_key]
    stored = hub.create(payload["type"], body, OWNER)
    key = payload.get("key")
    if key:
        keys[str(key)] = stored["id"]
    if payload["type"] == "project" and body.get("title") == "Europe Trip":
        keys["trip"] = stored["id"]
    if payload["type"] == "project" and body.get("title") == "Q3 Planning":
        keys["work"] = stored["id"]
    return {"ok": True, "object_id": stored["id"]}


def _apply_tick(
    hub: Hub,
    tick: dict[str, Any],
    *,
    keys: dict[str, str],
    actor: str,
    ticks: list[dict[str, Any]],
) -> dict[str, Any]:
    action = tick["action"]
    payload = tick["input"]
    if action == "create":
        return _apply_create(hub, tick, keys)
    if action == "supersede":
        obj_id = keys[str(payload["key"])]
        stored = hub.supersede(obj_id, payload["body"], OWNER)
        successor = stored["successor"]
        keys[str(payload["key"])] = successor["id"]
        return {"ok": True, "object_id": successor["id"]}
    if action == "search":
        data = hub.search(payload["query"], actor=actor, purpose=payload.get("purpose"))
        results = data.get("results") or []
        return {"ok": True, "hit_count": len(results), "withheld": data.get("redactions") or []}
    if action == "get_context_contract":
        contract = hub.get_context_contract(actor, payload["purpose"])
        return {
            "ok": True,
            "situation": contract.get("situation"),
            "project_id": situation_project_id(contract),
            "cited_ids": cited_ids(contract),
            "withheld": contract.get("omissions") or [],
        }
    if action == "brief":
        pid = keys[str(payload["project_key"])]
        brief = hub.brief(pid, actor=actor)
        project = brief.get("project") or {}
        title = brief.get("title") or project.get("title")
        return {"ok": True, "object_id": pid, "title": title}
    if action == "propose_memory":
        body = dict(payload["body"])
        project_key = body.pop("project_key", None)
        if project_key:
            body["project_id"] = keys[project_key]
        now = now_iso()
        mem = {
            "id": new_id("memory"),
            "type": "memory",
            "kind": body.get("kind", "semantic"),
            "statement": body["statement"],
            "project_id": body.get("project_id"),
            "owner": hub.person_id(),
            "space_id": "personal",
            "created_at": now,
            "updated_at": now,
            "labels": ["sim", "persona:lived-stretch"],
            "classification": "personal",
            "source_refs": [],
            "confidence": 0.6,
            "authority": "proposed",
            "retention": {"mode": "until_revoked"},
            "policy_tags": [],
            "version": 1,
            "sensitivity_flags": [],
        }
        proposed = hub.propose_memory(mem, actor, [])
        return {"ok": True, "proposal_id": proposed["id"]}
    if action == "decide_proposal":
        after = int(payload["after_seq"])
        prior = next(t for t in ticks if t["seq"] == after)
        proposal_id = (prior.get("result") or {})["proposal_id"]
        stored = hub.decide_proposal(proposal_id, bool(payload.get("accept", True)))
        return {"ok": True, "object_id": stored.get("id"), "proposal_id": proposal_id}
    raise SimRefused("forbidden_action", action)


def run_sim(
    *,
    data_dir: Path | None = None,
    persona_id: str = "lived-stretch",
    delay_ms: int = 0,
    target: str = "isolated",
    confirm: str = "",
    everyday_dir: Path | None = None,
    paired_assistant: bool = False,
    auto_accept: bool = True,
) -> dict[str, Any]:
    root = resolve_data_dir(
        data_dir=data_dir, target=target, confirm=confirm, everyday_dir=everyday_dir
    )
    existing = load_run(root)
    if existing and existing.get("status") == "running":
        raise SimRefused("in_flight")
    ticks = _expand_auto_accept(compile_persona(persona_id), auto_accept)
    via = "paired_assistant" if paired_assistant else "in_process_pair"
    for tick in ticks:
        if tick["role"] == "assistant":
            tick["via"] = via
        else:
            tick["via"] = "in_process_pair"
    hub = Hub(root, plain=True)
    try:
        _ensure_setup(hub)
        paired = mint_assistant(hub)
        run = {
            "schema_version": 1,
            "id": new_id("simrun"),
            "persona_id": persona_id,
            "status": "running",
            "target": target,
            "data_dir": str(root),
            "paired_assistant": paired_assistant,
            "auto_accept": auto_accept,
            "delay_ms": delay_ms,
            "current_seq": 0,
            "started_at": _now(),
            "ended_at": None,
            "connection_id": paired["connection_id"],
            "object_count": 0,
            "query_count": 0,
            "trip_project_id": None,
            "work_project_id": None,
        }
        save_run(root, run)
        save_ticks(root, ticks)
        keys: dict[str, str] = {}
        for tick in ticks:
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)
            actor = OWNER if tick["role"] == "owner" else paired["connection_id"]
            try:
                result = _apply_tick(hub, tick, keys=keys, actor=actor, ticks=ticks)
                tick["status"] = "applied"
                tick["result"] = result
                tick["error"] = None
            except Exception as exc:
                tick["status"] = "failed"
                tick["result"] = {"ok": False}
                tick["error"] = str(exc)
                run["status"] = "failed"
                run["ended_at"] = _now()
                run["current_seq"] = tick["seq"]
                save_ticks(root, ticks)
                save_run(root, run)
                raise
            run["current_seq"] = tick["seq"]
            if tick["action"] == "create" and tick["status"] == "applied":
                run["object_count"] = _object_count(hub)
            if tick["action"] in QUERY_ACTIONS and tick["status"] == "applied":
                run["query_count"] = int(run["query_count"]) + 1
            run["trip_project_id"] = keys.get("trip")
            run["work_project_id"] = keys.get("work")
            save_ticks(root, ticks)
            save_run(root, run)
        run["status"] = "complete"
        run["ended_at"] = _now()
        run["object_count"] = _object_count(hub)
        save_run(root, run)
        return run
    finally:
        hub.close()


class ThreadedRun:
    def __init__(
        self,
        hub: Hub,
        data_dir: Path,
        ticks: list[dict[str, Any]],
        run: dict[str, Any],
        connection_id: str,
        delay_ms: int,
    ) -> None:
        self.hub = hub
        self.data_dir = data_dir
        self.ticks = ticks
        self.run = run
        self.connection_id = connection_id
        self.delay_ms = delay_ms
        self.lock = threading.Lock()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_flag = False
        self.keys: dict[str, str] = {}
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def pause(self) -> None:
        self.pause_event.clear()
        with self.lock:
            if self.run["status"] == "running":
                self.run["status"] = "paused"
                save_run(self.data_dir, self.run)

    def resume(self) -> None:
        with self.lock:
            if self.run["status"] == "paused":
                self.run["status"] = "running"
                save_run(self.data_dir, self.run)
        self.pause_event.set()

    def stop(self) -> None:
        self.stop_flag = True
        self.pause_event.set()

    def _loop(self) -> None:
        for tick in self.ticks:
            self.pause_event.wait()
            if self.stop_flag:
                with self.lock:
                    self.run["status"] = "stopped"
                    self.run["ended_at"] = _now()
                    save_run(self.data_dir, self.run)
                return
            if self.delay_ms > 0:
                time.sleep(self.delay_ms / 1000)
            with self.lock:
                actor = OWNER if tick["role"] == "owner" else self.connection_id
                try:
                    result = _apply_tick(
                        self.hub, tick, keys=self.keys, actor=actor, ticks=self.ticks
                    )
                    tick["status"] = "applied"
                    tick["result"] = result
                    tick["error"] = None
                except Exception as exc:
                    tick["status"] = "failed"
                    tick["result"] = {"ok": False}
                    tick["error"] = str(exc)
                    self.run["status"] = "failed"
                    self.run["ended_at"] = _now()
                    self.run["current_seq"] = tick["seq"]
                    save_ticks(self.data_dir, self.ticks)
                    save_run(self.data_dir, self.run)
                    return
                self.run["current_seq"] = tick["seq"]
                if tick["action"] == "create":
                    self.run["object_count"] = _object_count(self.hub)
                if tick["action"] in QUERY_ACTIONS:
                    self.run["query_count"] = int(self.run["query_count"]) + 1
                self.run["trip_project_id"] = self.keys.get("trip")
                self.run["work_project_id"] = self.keys.get("work")
                save_ticks(self.data_dir, self.ticks)
                save_run(self.data_dir, self.run)
        with self.lock:
            self.run["status"] = "complete"
            self.run["ended_at"] = _now()
            self.run["object_count"] = _object_count(self.hub)
            save_run(self.data_dir, self.run)


def start_threaded(
    hub: Hub,
    *,
    persona_id: str = "lived-stretch",
    delay_ms: int = 200,
    paired_assistant: bool = False,
    auto_accept: bool = True,
    target: str = "isolated",
) -> ThreadedRun:
    data_dir = Path(hub.data_dir)
    existing = load_run(data_dir)
    if existing and existing.get("status") == "running":
        raise SimRefused("in_flight")
    _ensure_setup(hub)
    ticks = _expand_auto_accept(compile_persona(persona_id), auto_accept)
    via = "paired_assistant" if paired_assistant else "in_process_pair"
    for tick in ticks:
        tick["via"] = via if tick["role"] == "assistant" else "in_process_pair"
    paired = mint_assistant(hub)
    run = {
        "schema_version": 1,
        "id": new_id("simrun"),
        "persona_id": persona_id,
        "status": "running",
        "target": target,
        "data_dir": str(data_dir),
        "paired_assistant": paired_assistant,
        "auto_accept": auto_accept,
        "delay_ms": delay_ms,
        "current_seq": 0,
        "started_at": _now(),
        "ended_at": None,
        "connection_id": paired["connection_id"],
        "object_count": 0,
        "query_count": 0,
        "trip_project_id": None,
        "work_project_id": None,
    }
    save_run(data_dir, run)
    save_ticks(data_dir, ticks)
    session = ThreadedRun(hub, data_dir, ticks, run, paired["connection_id"], delay_ms)
    session.start()
    return session
