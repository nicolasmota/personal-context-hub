from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pch_lab.devloop.refuse import LoopRefused, refuse_start
from pch_lab.devloop.runfile import (
    active_feature_dir,
    find_bar_file,
    load_run,
    pack_complete,
    persist_feature_dir,
    repo_root,
    run_path,
    save_run,
    sha256_file,
)

STAGE_ORDER = (
    "specify",
    "clarify",
    "freeze_bar",
    "plan",
    "gauntlet",
    "tasks",
    "analyze",
    "implement",
    "test",
    "delivery",
    "converge",
    "complete",
)

SKILL_FOR_STAGE = {
    "specify": "speckit-specify",
    "clarify": "speckit-clarify",
    "freeze_bar": "gauntlet-bar",
    "plan": "speckit-plan",
    "gauntlet": "gauntlet-critics",
    "tasks": "speckit-tasks",
    "analyze": "speckit-analyze",
    "implement": "speckit-implement",
    "test": "make-test",
    "delivery": "delivery-validate",
    "converge": "speckit-converge",
    "complete": "none",
}

MAX_GAUNTLET_ROUNDS = 3
MAX_TEST_REPAIRS = 2
IN_FLIGHT = frozenset({"running", "blocked_on_person"})


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _empty_stages() -> dict[str, Any]:
    return {
        sid: {
            "id": sid,
            "outcome": None,
            "started_at": None,
            "ended_at": None,
            "evidence": None,
        }
        for sid in STAGE_ORDER
    }


def new_run(
    *,
    feature_dir: str,
    mode: str,
    source: str,
    source_value: str | None,
    current_stage: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "feature_dir": feature_dir,
        "mode": mode,
        "source": source,
        "source_value": source_value,
        "current_stage": current_stage,
        "status": "running",
        "stop_reason": None,
        "refuse_reason": None,
        "bar_path": None,
        "bar_sha256": None,
        "gauntlet_round": 0,
        "test_repair_round": 0,
        "stages": _empty_stages(),
        "unmet_items": [],
        "updated_at": _now(),
    }


def infer_stage(feature_path: Path) -> str:
    if not (feature_path / "spec.md").is_file():
        return "specify"
    if find_bar_file(feature_path) is None:
        return "freeze_bar"
    if not pack_complete(feature_path):
        return "plan"
    if not (feature_path / "tasks.md").is_file():
        return "gauntlet"
    return "tasks"


def parse_roadmap_epics(text: str) -> list[tuple[str, str | None]]:
    epics: list[tuple[str, str | None]] = []
    current: str | None = None
    spec: str | None = None
    heading = re.compile(r"^###\s+(E\d+)")
    spec_line = re.compile(r"\*\*Spec:\*\*\s+`([^`]+)`|^\*\*Spec:\*\*\s+[—-]\s*$")
    for raw in text.splitlines():
        hm = heading.match(raw)
        if hm:
            if current is not None:
                epics.append((current, spec))
            current = hm.group(1)
            spec = None
            continue
        if current is None:
            continue
        sm = spec_line.search(raw)
        if sm:
            if sm.group(1):
                spec = sm.group(1).strip().rstrip("/")
            else:
                spec = None
    if current is not None:
        epics.append((current, spec))
    return epics


def tasks_all_checked(repo: Path, spec: str) -> bool:
    tasks = repo / spec / "tasks.md"
    if not tasks.is_file():
        return False
    text = tasks.read_text(encoding="utf-8")
    return re.search(r"^- \[ \] T\d+", text, flags=re.MULTILINE) is None


def select_roadmap_dir(repo: Path) -> tuple[str, str | None]:
    roadmap = repo / "docs" / "ROADMAP.md"
    epics = parse_roadmap_epics(roadmap.read_text(encoding="utf-8"))
    for epic_id, spec in epics:
        if spec is None:
            return ".specify/pending", epic_id
        run_file = run_path(repo, spec)
        if run_file.is_file():
            data = json.loads(run_file.read_text(encoding="utf-8"))
            if data.get("status") == "complete":
                continue
            return spec, epic_id
        if tasks_all_checked(repo, spec):
            continue
        return spec, epic_id
    raise LoopRefused("empty_start", "No unfinished era epic on the roadmap")


def complete_allowed(run: dict[str, Any]) -> bool:
    if run.get("status") == "failed":
        return False
    if run.get("unmet_items"):
        return False
    if run.get("mode") == "design-only":
        gauntlet = run.get("stages", {}).get("gauntlet") or {}
        return gauntlet.get("outcome") == "pass"
    test = run.get("stages", {}).get("test") or {}
    evidence = test.get("evidence") or {}
    if evidence.get("exit_code") != 0:
        return False
    delivery = run.get("stages", {}).get("delivery") or {}
    if delivery.get("outcome") != "pass":
        return False
    sc_results = (delivery.get("evidence") or {}).get("sc_results") or {}
    if not sc_results or any(value != "pass" for value in sc_results.values()):
        return False
    red = (delivery.get("evidence") or {}).get("red_before_green") or {}
    if not red or any(value is not True for value in red.values()):
        return False
    return True


def start(
    *,
    mode: str = "full",
    desc: str | None = None,
    epic: str | None = None,
    dir: str | None = None,
    roadmap: bool = False,
    resume: bool = False,
    redo: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    refuse_start(desc=desc, epic=epic, dir=dir, roadmap=roadmap)
    source = "desc"
    source_value: str | None = desc
    feature_dir: str
    if dir:
        source = "dir"
        source_value = dir
        feature_dir = dir.replace("\\", "/").rstrip("/")
    elif epic:
        source = "epic"
        source_value = epic
        feature_dir = _epic_to_dir(root, epic)
    elif roadmap:
        source = "roadmap"
        feature_dir, source_value = select_roadmap_dir(root)
    else:
        feature_dir = ".specify/pending"
        (root / feature_dir).mkdir(parents=True, exist_ok=True)
        source = "desc"
        source_value = desc

    existing_path = run_path(root, feature_dir)
    if existing_path.is_file() and not resume and not redo:
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        if existing.get("status") in IN_FLIGHT:
            raise LoopRefused("in_flight", "A run is already in progress for this spec folder")
    persist_feature_dir(root, feature_dir)
    if existing_path.is_file() and (resume or redo):
        run = json.loads(existing_path.read_text(encoding="utf-8"))
        if redo:
            run["current_stage"] = redo
            run["status"] = "running"
            run["stop_reason"] = None
        elif run.get("status") == "stopped":
            run["status"] = "running"
            run["stop_reason"] = None
        run["updated_at"] = _now()
        save_run(root, run)
        return run

    current = infer_stage(root / feature_dir)
    run = new_run(
        feature_dir=feature_dir,
        mode=mode,
        source=source,
        source_value=source_value,
        current_stage=current,
    )
    save_run(root, run)
    return run


def _epic_to_dir(repo: Path, epic: str) -> str:
    token = epic.strip()
    if not token.upper().startswith("E"):
        token = f"E{token}" if token.isdigit() else token
    roadmap = (repo / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    wanted = f"E{epic.strip().lstrip('Ee')}"
    for epic_id, spec in parse_roadmap_epics(roadmap):
        if epic_id.upper() in {token.upper(), wanted.upper()}:
            if spec is None:
                return ".specify/pending"
            return spec
    raise LoopRefused("empty_start", f"Unknown epic {epic}")


def next_step(repo: Path | None = None, feature_dir: str | None = None) -> dict[str, Any]:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    stage = run["current_stage"]
    skill = SKILL_FOR_STAGE.get(stage, stage)
    return {
        "feature_dir": directory,
        "stage": stage,
        "command": f"run skill {skill} then loop record --stage {stage}",
        "skill": skill,
        "status": run["status"],
        "gauntlet_round": run.get("gauntlet_round", 0),
    }


def record(
    *,
    stage: str,
    outcome: str,
    sc_results: dict[str, str] | None = None,
    red_before_green: dict[str, bool] | None = None,
    repo: Path | None = None,
    feature_dir: str | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    feat = root / directory
    if run["status"] == "failed":
        raise ValueError("Run already failed")
    if stage == "plan":
        if not run.get("bar_sha256"):
            raise ValueError("Cannot record plan before the Gauntlet bar is frozen")
        bar = find_bar_file(feat)
        if bar is None or sha256_file(bar) != run["bar_sha256"]:
            raise ValueError("Gauntlet bar missing or hash drifted (bar)")
        if not pack_complete(feat):
            raise ValueError("Plan pack files missing")
    if stage == "freeze_bar":
        bar = find_bar_file(feat)
        if bar is None:
            raise ValueError("No PLAN-BAR.md or SPEC-BAR.md to freeze")
        run["bar_path"] = str(bar.relative_to(root)).replace("\\", "/")
        run["bar_sha256"] = sha256_file(bar)
        run["current_stage"] = "plan"
    rec = run["stages"].setdefault(stage, {"id": stage, "outcome": None, "evidence": None})
    rec["outcome"] = outcome
    rec["ended_at"] = _now()
    if stage == "delivery":
        evidence = rec.get("evidence") or {}
        if sc_results is not None:
            evidence["sc_results"] = sc_results
        if red_before_green is not None:
            evidence["red_before_green"] = red_before_green
        rec["evidence"] = evidence
    if outcome == "blocked_on_person":
        run["status"] = "blocked_on_person"
        run["updated_at"] = _now()
        save_run(root, run)
        return run
    if outcome == "fail":
        if stage in {"test", "delivery"}:
            run["test_repair_round"] = int(run.get("test_repair_round") or 0) + 1
            if run["test_repair_round"] > MAX_TEST_REPAIRS:
                run["status"] = "failed"
                run["stop_reason"] = "budget_exhausted"
            else:
                run["current_stage"] = "implement"
        else:
            run["status"] = "failed"
            run["stop_reason"] = "budget_exhausted"
        run["updated_at"] = _now()
        save_run(root, run)
        return run
    if outcome == "pass" and stage != "freeze_bar":
        _advance_after_pass(run, stage)
    if stage == "delivery" and outcome == "pass":
        if complete_allowed(run):
            run["status"] = "complete"
            run["current_stage"] = "complete"
            run["stages"]["complete"]["outcome"] = "pass"
        elif run.get("unmet_items"):
            run["current_stage"] = "converge"
    run["updated_at"] = _now()
    save_run(root, run)
    return run


def _advance_after_pass(run: dict[str, Any], stage: str) -> None:
    nxt = {
        "specify": "freeze_bar",
        "clarify": "freeze_bar",
        "plan": "gauntlet",
        "gauntlet": "complete" if run["mode"] == "design-only" else "tasks",
        "tasks": "analyze",
        "analyze": "implement",
        "implement": "test",
        "test": "delivery",
        "converge": "implement",
    }
    if stage == "gauntlet" and run["mode"] == "design-only":
        run["current_stage"] = "complete"
        run["status"] = "complete"
        run["stages"]["complete"]["outcome"] = "pass"
        return
    if stage in nxt:
        run["current_stage"] = nxt[stage]


def record_verdict(
    *,
    critic: str,
    verdict: str,
    round: int,
    failing: str | None = None,
    repo: Path | None = None,
    feature_dir: str | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    feat = root / directory
    bar = find_bar_file(feat)
    if bar is None or not run.get("bar_sha256") or sha256_file(bar) != run["bar_sha256"]:
        raise ValueError("Gauntlet bar hash drifted")
    rec = run["stages"].setdefault("gauntlet", {"id": "gauntlet", "outcome": None, "evidence": {}})
    evidence = rec.get("evidence") or {}
    verdicts: list[dict[str, Any]] = list(evidence.get("verdicts") or [])
    failing_ids = [part.strip() for part in (failing or "").split(",") if part.strip()]
    verdicts.append(
        {
            "critic_id": critic,
            "round": round,
            "verdict": verdict,
            "failing_criteria": failing_ids,
        }
    )
    evidence["verdicts"] = verdicts
    rec["evidence"] = evidence
    pair = [item for item in verdicts if item["round"] == round]
    critics = {item["critic_id"] for item in pair}
    if "A" in critics and "B" in critics:
        wins = [item["verdict"] == "WIN" for item in pair if item["critic_id"] in {"A", "B"}]
        if len(wins) >= 2 and all(item["verdict"] == "WIN" for item in pair):
            rec["outcome"] = "pass"
            rec["ended_at"] = _now()
            if run["mode"] == "design-only":
                run["status"] = "complete"
                run["current_stage"] = "complete"
                run["stages"]["complete"]["outcome"] = "pass"
            else:
                run["current_stage"] = "tasks"
        else:
            run["gauntlet_round"] = max(int(run.get("gauntlet_round") or 0), round)
            rec["outcome"] = None
            if round >= MAX_GAUNTLET_ROUNDS:
                run["status"] = "failed"
                run["stop_reason"] = "budget_exhausted"
            else:
                run["current_stage"] = "plan"
    run["updated_at"] = _now()
    save_run(root, run)
    return run


def record_evidence(
    *,
    command: str,
    exit_code: int,
    summary: str,
    repo: Path | None = None,
    feature_dir: str | None = None,
) -> dict[str, Any]:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    rec = run["stages"].setdefault("test", {"id": "test", "outcome": None, "evidence": None})
    rec["evidence"] = {
        "command": command,
        "exit_code": exit_code,
        "summary": summary,
        "recorded_at": _now(),
    }
    if rec.get("outcome") is None and exit_code == 0:
        rec["outcome"] = "pass"
    if exit_code != 0:
        rec["outcome"] = "fail"
        run["test_repair_round"] = int(run.get("test_repair_round") or 0) + 1
        if run["test_repair_round"] > MAX_TEST_REPAIRS:
            run["status"] = "failed"
            run["stop_reason"] = "budget_exhausted"
        else:
            run["current_stage"] = "implement"
    run["updated_at"] = _now()
    save_run(root, run)
    return run


def stop(repo: Path | None = None, feature_dir: str | None = None) -> dict[str, Any]:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    run["status"] = "stopped"
    run["stop_reason"] = "person_stop"
    run["updated_at"] = _now()
    save_run(root, run)
    return run


def status_text(repo: Path | None = None, feature_dir: str | None = None) -> str:
    root = repo or repo_root()
    directory = feature_dir or active_feature_dir(root)
    run = load_run(root, directory)
    passed = [sid for sid, rec in run["stages"].items() if rec.get("outcome") == "pass"]
    verdicts = ((run["stages"].get("gauntlet") or {}).get("evidence") or {}).get("verdicts") or []
    last_round = verdicts[-1]["round"] if verdicts else 0
    latest = [item for item in verdicts if item.get("round") == last_round]
    a = next((item["verdict"] for item in latest if item["critic_id"] == "A"), "-")
    b = next((item["verdict"] for item in latest if item["critic_id"] == "B"), "-")
    test_ev = (run["stages"].get("test") or {}).get("evidence")
    if not test_ev:
        evidence_line = "none"
    else:
        evidence_line = (
            f"{test_ev.get('command')} exit {test_ev.get('exit_code')} "
            f"at {test_ev.get('recorded_at')}"
        )
    stop_reason = run.get("stop_reason") or ""
    round_n = run.get("gauntlet_round", 0)
    return (
        f"feature: {directory}\n"
        f"mode: {run['mode']}\n"
        f"status: {run['status']}\n"
        f"stage: {run['current_stage']} (round {round_n}/{MAX_GAUNTLET_ROUNDS})\n"
        f"passed: {', '.join(passed) if passed else '(none)'}\n"
        f"latest verdicts: A={a} B={b}\n"
        f"test evidence: {evidence_line}\n"
        f"stop_reason: {stop_reason}\n"
    )
