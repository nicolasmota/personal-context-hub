from __future__ import annotations

import argparse
import json
import os
import sys

from pch_sdk.client import Client
from pch_sdk.local_cli import (
    archive_export,
    archive_import,
    compile_contract,
    evidence_add,
    evolve,
    experience_add,
    vault_init,
)
from pch_sdk.mcp_bridge import main as bridge_main
from pch_sdk.plugin_kit import main as plugin_kit_main


def demo(base: str, code: str | None, token: str | None) -> None:
    client = Client(base, token or "")
    if code:
        result = client.pair(code)
        print(json.dumps(result, indent=2))
        token = result["token"]
        client.token = token
    print(
        json.dumps(client.call("search_personal_context", query="Atlas", purpose="demo"), indent=2)
    )


def main(argv: list[str] | None = None) -> None:
    seq = list(argv) if argv is not None else sys.argv[1:]
    if seq[:1] in (["loop"], ["sim"], ["eval"]):
        verb = seq[0]
        sys.stderr.write(f"pch-sdk does not run {verb}. Use: uv run pch-lab {verb}\n")
        raise SystemExit(2)
    parser = argparse.ArgumentParser(prog="pch-sdk")
    sub = parser.add_subparsers(dest="cmd")
    demo_p = sub.add_parser("demo-agent")
    demo_p.add_argument("--pair", dest="code")
    demo_p.add_argument("--base", default="http://127.0.0.1:8765")
    demo_p.add_argument("--token", default="")
    bridge_p = sub.add_parser("mcp-bridge")
    bridge_p.add_argument("--token", default=os.environ.get("PCH_TOKEN", ""))
    bridge_p.add_argument("--base", default=os.environ.get("PCH_BASE", "http://127.0.0.1:8765"))
    plugin_p = sub.add_parser("plugin")
    plugin_p.add_argument("plugin_args", nargs=argparse.REMAINDER)
    for name in (
        "vault-init",
        "experience-add",
        "evidence-add",
        "evolve",
        "compile",
        "archive-export",
        "archive-import",
    ):
        command = sub.add_parser(name)
        command.add_argument("--data-dir", required=True)
        if name == "vault-init":
            command.add_argument("--name", required=True)
        if name == "experience-add":
            command.add_argument("--action", required=True)
            command.add_argument("--context", required=True)
            command.add_argument("--outcome", required=True)
            command.add_argument("--at", required=True)
            command.add_argument("--provenance", required=True)
            command.add_argument("--feedback", default=None)
            command.add_argument("--lesson", default=None)
            command.add_argument("--confidence", type=float, default=1.0)
        if name == "evidence-add":
            command.add_argument("--kind", required=True)
            command.add_argument("--source", required=True)
            command.add_argument("--authority", required=True)
            command.add_argument("--at", required=True)
            command.add_argument("--statement", required=True)
            command.add_argument("--confidence", type=float, default=1.0)
            command.add_argument("--verification", default="unverified")
        if name == "evolve":
            command.add_argument("--subject", required=True)
            command.add_argument("--value", required=True)
            command.add_argument("--reason", required=True)
            command.add_argument("--experience", default=None)
            command.add_argument("--evidence", default=None)
            command.add_argument("--condition", default=None)
        if name == "compile":
            command.add_argument("--purpose", required=True)
            command.add_argument("--budget", type=int, default=None)
            command.add_argument("--as-of", dest="as_of", default=None)
            command.add_argument("--actor", default=None)
        if name == "archive-export":
            command.add_argument("--dest", required=True)
            command.add_argument("--passphrase", required=True)
        if name == "archive-import":
            command.add_argument("--src", required=True)
            command.add_argument("--passphrase", required=True)
    args = parser.parse_args(seq)
    if args.cmd == "demo-agent":
        demo(args.base, args.code, args.token or None)
        return
    if args.cmd == "mcp-bridge":
        bridge_main(args.token or None, args.base)
        return
    if args.cmd == "plugin":
        plugin_kit_main(args.plugin_args)
        return
    if args.cmd == "vault-init":
        vault_init(args.data_dir, args.name)
        return
    if args.cmd == "experience-add":
        experience_add(args.data_dir, args)
        return
    if args.cmd == "evidence-add":
        evidence_add(args.data_dir, args)
        return
    if args.cmd == "evolve":
        evolve(args.data_dir, args)
        return
    if args.cmd == "compile":
        compile_contract(args.data_dir, args)
        return
    if args.cmd == "archive-export":
        archive_export(args.data_dir, args)
        return
    if args.cmd == "archive-import":
        archive_import(args.data_dir, args)
        return
    parser.print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
