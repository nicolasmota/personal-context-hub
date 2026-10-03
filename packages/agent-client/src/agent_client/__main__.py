from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agent_client.client import Client
from agent_client.local_cli import (
    archive_export,
    archive_import,
    compile_contract,
    connection_revoke,
    connections_list,
    evidence_add,
    evolve,
    experience_add,
    grant_create,
    import_memories,
    link_mint,
    proposals_decide,
    proposals_list,
    show_token,
    vault_init,
)
from agent_client.mcp_bridge import main as bridge_main
from agent_client.service_cmd import (
    install_service,
    logs_service,
    status_service,
    uninstall_service,
)


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
        sys.stderr.write(f"personal-context does not run {verb}. Use: uv run personal-context-lab {verb}\n")
        raise SystemExit(2)
    parser = argparse.ArgumentParser(prog="personal-context")
    sub = parser.add_subparsers(dest="cmd")
    demo_p = sub.add_parser("demo-agent")
    demo_p.add_argument("--pair", dest="code")
    demo_p.add_argument("--base", default="http://127.0.0.1:8765")
    demo_p.add_argument("--token", default="")
    bridge_p = sub.add_parser("mcp-bridge")
    bridge_p.add_argument("--token", default=os.environ.get("PERSONAL_CONTEXT_TOKEN", ""))
    bridge_p.add_argument("--base", default=os.environ.get("PERSONAL_CONTEXT_BASE", "http://127.0.0.1:8765"))
    for name in (
        "vault-init",
        "experience-add",
        "evidence-add",
        "evolve",
        "compile",
        "contract",
        "archive-export",
        "archive-import",
        "token",
        "link",
        "connections",
        "grant",
        "revoke",
        "import-memories",
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
            command.add_argument("--project", default=None)
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
        if name in ("compile", "contract"):
            command.add_argument("--purpose", required=True)
            command.add_argument("--budget", type=int, default=None)
            command.add_argument("--as-of", dest="as_of", default=None)
            command.add_argument("--actor", default=None)
        if name == "link":
            command.add_argument("--name", required=True)
        if name == "grant":
            command.add_argument("--connection", required=True)
            command.add_argument("--preset", required=True)
            command.add_argument("--project", default=None)
        if name == "revoke":
            command.add_argument("--connection", required=True)
        if name == "import-memories":
            command.add_argument("--src", required=True)
            command.add_argument("--provider", choices=("chatgpt", "claude"), default=None)
        if name == "archive-export":
            command.add_argument("--dest", required=True)
            command.add_argument("--passphrase", required=True)
        if name == "archive-import":
            command.add_argument("--src", required=True)
            command.add_argument("--passphrase", required=True)
    proposals = sub.add_parser("proposals")
    proposals.add_argument("--data-dir", required=True)
    proposal_actions = proposals.add_subparsers(dest="proposal_action", required=True)
    proposal_actions.add_parser("list")
    accept = proposal_actions.add_parser("accept")
    accept.add_argument("proposal_id")
    reject = proposal_actions.add_parser("reject")
    reject.add_argument("proposal_id")
    service = sub.add_parser("service")
    service_actions = service.add_subparsers(dest="service_action", required=True)
    for service_name in ("install", "uninstall", "status", "logs"):
        service_command = service_actions.add_parser(service_name)
        service_command.add_argument(
            "--data-dir",
            default=str(Path.home() / ".personal-context"),
        )
        if service_name == "install":
            service_command.add_argument("--port", type=int, default=8765)
            service_command.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(seq)
    if args.cmd == "demo-agent":
        demo(args.base, args.code, args.token or None)
        return
    if args.cmd == "mcp-bridge":
        bridge_main(args.token or None, args.base)
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
    if args.cmd in ("compile", "contract"):
        compile_contract(args.data_dir, args)
        return
    if args.cmd == "token":
        show_token(args.data_dir)
        return
    if args.cmd == "link":
        link_mint(args.data_dir, args.name)
        return
    if args.cmd == "connections":
        connections_list(args.data_dir)
        return
    if args.cmd == "grant":
        grant_create(args.data_dir, args)
        return
    if args.cmd == "revoke":
        connection_revoke(args.data_dir, args.connection)
        return
    if args.cmd == "import-memories":
        import_memories(args.data_dir, args)
        return
    if args.cmd == "proposals":
        if args.proposal_action == "list":
            proposals_list(args.data_dir)
            return
        proposals_decide(
            args.data_dir,
            args.proposal_id,
            accept=args.proposal_action == "accept",
        )
        return
    if args.cmd == "archive-export":
        archive_export(args.data_dir, args)
        return
    if args.cmd == "archive-import":
        archive_import(args.data_dir, args)
        return
    if args.cmd == "service":
        data_dir = Path(args.data_dir)
        if args.service_action == "install":
            print(json.dumps(install_service(data_dir=data_dir, port=args.port, host=args.host)))
            return
        if args.service_action == "uninstall":
            print(json.dumps(uninstall_service(data_dir=data_dir)))
            return
        if args.service_action == "status":
            print(json.dumps(status_service(data_dir=data_dir)))
            return
        print(logs_service(data_dir=data_dir))
        return
    parser.print_help()
    raise SystemExit(1)


if __name__ == "__main__":
    main()
