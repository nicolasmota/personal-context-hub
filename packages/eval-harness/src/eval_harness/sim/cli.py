from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pch_lab.sim.persona import dump_ticks
from pch_lab.sim.records import load_run
from pch_lab.sim.refuse import SimRefused
from pch_lab.sim.runner import default_sim_dir, run_sim


def dispatch_sim(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="pch-lab sim")
    sub = parser.add_subparsers(dest="sim_cmd", required=True)
    dump_p = sub.add_parser("dump")
    dump_p.add_argument("--persona", default="lived-stretch")
    run_p = sub.add_parser("run")
    run_p.add_argument("--persona", default="lived-stretch")
    run_p.add_argument("--delay-ms", type=int, default=0)
    run_p.add_argument("--data-dir", type=Path)
    run_p.add_argument("--target", default="isolated", choices=("isolated", "everyday"))
    run_p.add_argument("--confirm", default="")
    run_p.add_argument("--paired-assistant", action="store_true")
    run_p.add_argument("--print-mcp-recipe", action="store_true")
    run_p.add_argument("--leave-proposals", action="store_true")
    status_p = sub.add_parser("status")
    status_p.add_argument("--data-dir", type=Path)
    for name in ("pause", "resume", "stop"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.sim_cmd == "dump":
            ticks = dump_ticks(args.persona)
            sys.stdout.write(json.dumps(ticks, indent=2) + "\n")
            return 0
        if args.sim_cmd == "run":
            data_dir = args.data_dir or default_sim_dir()
            run = run_sim(
                data_dir=data_dir,
                persona_id=args.persona,
                delay_ms=args.delay_ms,
                target=args.target,
                confirm=args.confirm,
                paired_assistant=args.paired_assistant,
                auto_accept=not args.leave_proposals,
            )
            if args.print_mcp_recipe and args.paired_assistant:
                recipe = {
                    "command": "uv",
                    "args": ["run", "pch-sdk", "mcp-bridge"],
                    "env": {
                        "PCH_BASE": "http://127.0.0.1:8765",
                        "PCH_TOKEN": "<pair token from Hub connections — not written to disk>",
                    },
                }
                sys.stdout.write(json.dumps({"run": run, "mcp_recipe": recipe}, indent=2) + "\n")
            else:
                sys.stdout.write(json.dumps(run, indent=2) + "\n")
            return 0 if run.get("status") == "complete" else 1
        data_dir = args.data_dir or default_sim_dir()
        run = load_run(data_dir)
        if run is None:
            sys.stderr.write("error: no sim run\n")
            return 1
        if args.sim_cmd == "status":
            sys.stdout.write(
                f"id: {run.get('id')}\nstatus: {run.get('status')}\n"
                f"seq: {run.get('current_seq')}\nobjects: {run.get('object_count')}\n"
                f"queries: {run.get('query_count')}\n"
            )
            return 0
        sys.stderr.write(
            "error: pause/resume/stop apply to the server-hosted simulator\n"
        )
        return 1
    except SimRefused as err:
        sys.stderr.write(f"refused: {err.reason}\n")
        return 2
