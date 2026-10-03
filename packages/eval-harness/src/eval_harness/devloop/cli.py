from __future__ import annotations

import argparse
import json
import sys

from pch_lab.devloop.refuse import LoopRefused
from pch_lab.devloop.stages import (
    next_step,
    record,
    record_evidence,
    record_verdict,
    start,
    status_text,
    stop,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pch-lab")
    sub = parser.add_subparsers(dest="cmd")
    loop = sub.add_parser("loop", help="Speckit + Gauntlet development loop")
    loop_sub = loop.add_subparsers(dest="loop_cmd", required=True)
    start_p = loop_sub.add_parser("start", help="Start or resume a loop run")
    start_p.add_argument("--mode", choices=("full", "design-only"), default="full")
    start_p.add_argument("--desc")
    start_p.add_argument("--epic")
    start_p.add_argument("--dir")
    start_p.add_argument("--roadmap", action="store_true")
    start_p.add_argument("--resume", action="store_true")
    start_p.add_argument("--redo")
    loop_sub.add_parser("next", help="Print the current stage as JSON")
    rec = loop_sub.add_parser("record", help="Record a stage outcome")
    rec.add_argument("--stage", required=True)
    rec.add_argument("--outcome", required=True, choices=("pass", "fail", "blocked_on_person"))
    verdict = loop_sub.add_parser("record-verdict", help="Record a Gauntlet critic verdict")
    verdict.add_argument("--critic", required=True, choices=("A", "B"))
    verdict.add_argument("--verdict", required=True, choices=("WIN", "LOSE"))
    verdict.add_argument("--round", type=int, required=True)
    verdict.add_argument("--failing", default="")
    loop_sub.add_parser("status", help="Show run status")
    loop_sub.add_parser("stop", help="Stop the run")
    evidence = loop_sub.add_parser("evidence", help="Record test command evidence")
    evidence.add_argument("--command", required=True)
    evidence.add_argument("--exit-code", type=int, required=True)
    evidence.add_argument("--summary", required=True)
    return parser


def dispatch_loop(args: argparse.Namespace) -> int:
    try:
        if args.loop_cmd == "start":
            start(
                mode=args.mode,
                desc=args.desc,
                epic=args.epic,
                dir=args.dir,
                roadmap=args.roadmap,
                resume=args.resume,
                redo=args.redo,
            )
            sys.stdout.write(status_text())
            return 0
        if args.loop_cmd == "next":
            sys.stdout.write(json.dumps(next_step()) + "\n")
            return 0
        if args.loop_cmd == "record":
            record(stage=args.stage, outcome=args.outcome)
            sys.stdout.write(status_text())
            return 0
        if args.loop_cmd == "record-verdict":
            record_verdict(
                critic=args.critic,
                verdict=args.verdict,
                round=args.round,
                failing=args.failing or None,
            )
            sys.stdout.write(status_text())
            return 0
        if args.loop_cmd == "status":
            sys.stdout.write(status_text())
            return 0
        if args.loop_cmd == "stop":
            stop()
            sys.stdout.write(status_text())
            return 0
        if args.loop_cmd == "evidence":
            record_evidence(command=args.command, exit_code=args.exit_code, summary=args.summary)
            sys.stdout.write(status_text())
            return 0
    except LoopRefused as err:
        sys.stderr.write(f"refused: {err.reason}\n")
        return 2
    except (ValueError, FileNotFoundError, KeyError, OSError) as err:
        sys.stderr.write(f"error: {err}\n")
        return 1
    return 1
