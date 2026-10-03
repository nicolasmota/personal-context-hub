from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> None:
    seq = list(argv) if argv is not None else sys.argv[1:]
    if seq[:1] == ["loop"]:
        from pch_lab.devloop.cli import build_parser, dispatch_loop

        parser = build_parser()
        args = parser.parse_args(seq)
        raise SystemExit(dispatch_loop(args))
    if seq[:1] == ["bench"]:
        from pch_lab.benchmarks.cli import main as bench_main

        raise SystemExit(bench_main(seq[1:]))
    if seq[:1] == ["sim"]:
        from pch_lab.sim.cli import dispatch_sim

        raise SystemExit(dispatch_sim(seq[1:]))
    parser = argparse.ArgumentParser(prog="pch-lab")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("loop", help="Speckit + Gauntlet development loop")
    sub.add_parser("sim", help="Simulation harness")
    eval_p = sub.add_parser("eval", help="Evaluation harness")
    eval_p.add_argument("eval_cmd", nargs="?", default="run")
    if not seq:
        parser.print_help()
        raise SystemExit(1)
    args = parser.parse_args(seq)
    if args.cmd == "eval":
        if args.eval_cmd != "run":
            parser.error("usage: pch-lab eval run")
        from pch_lab.eval.harness import run_eval

        report = run_eval()
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
        raise SystemExit(0 if report["all_pass"] else 1)
    parser.print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
