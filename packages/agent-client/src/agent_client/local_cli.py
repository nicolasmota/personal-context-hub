from __future__ import annotations

import json
import os
from pathlib import Path

from portable_state.export import export_archive
from portable_state.import_ import IntegrityError, UnsupportedArchive, import_archive
from trust_kernel.errors import ValidationFailed
from trust_kernel.ingest.vendor_memory import import_vendor_file
from trust_kernel.service import OWNER, Hub


def _print(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _hub(data_dir: str) -> Hub:
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return Hub(path, plain=os.environ.get("PERSONAL_CONTEXT_PLAIN_SQLITE") == "1")


def vault_init(data_dir: str, name: str) -> None:
    hub = _hub(data_dir)
    try:
        created = hub.setup(name)
        _print({"owner_id": created["person"]["id"]})
    finally:
        hub.close()


def experience_add(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        row = hub.capture_experience(
            action=args.action,
            operating_context=args.context,
            outcome=args.outcome,
            occurred_at=args.at,
            provenance=args.provenance,
            feedback=args.feedback,
            lesson=args.lesson,
            confidence=args.confidence,
            project_id=args.project,
        )
        _print({"id": row["id"]})
    finally:
        hub.close()


def evidence_add(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        row = hub.record_evidence(
            kind=args.kind,
            source=args.source,
            authority_label=args.authority,
            observed_at=args.at,
            statement=args.statement,
            confidence=args.confidence,
            verification_status=args.verification,
            provenance_chain=[args.source],
        )
        _print({"id": row["id"]})
    finally:
        hub.close()


def evolve(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        try:
            result = hub.evolve(
                subject=args.subject,
                value=args.value,
                reason=args.reason,
                experience_ids=[args.experience] if args.experience else [],
                evidence_ids=[args.evidence] if args.evidence else [],
                condition=args.condition,
            )
        except ValidationFailed as exc:
            raise SystemExit(str(exc)) from exc
        _print(
            {
                "preference_id": result["preference"]["id"],
                "transition_id": result["transition"]["id"],
            }
        )
    finally:
        hub.close()


def compile_contract(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        actor = args.actor or OWNER
        contract = hub.get_context_contract(
            actor, args.purpose, max_items=args.budget, as_of=args.as_of
        )
        _print(contract)
    finally:
        hub.close()


def archive_export(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        result = export_archive(hub, Path(args.dest), args.passphrase, {})
        _print(result)
    finally:
        hub.close()


def archive_import(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        try:
            result = import_archive(hub, Path(args.src), args.passphrase)
        except (UnsupportedArchive, IntegrityError) as exc:
            raise SystemExit(str(exc)) from exc
        _print(result)
    finally:
        hub.close()


def show_token(data_dir: str) -> None:
    hub = _hub(data_dir)
    try:
        _print({"owner_credential": "owner.token", "owner_token": hub.owner_token})
    finally:
        hub.close()


def proposals_list(data_dir: str) -> None:
    hub = _hub(data_dir)
    try:
        rows = hub.list("proposal")
        _print(
            {
                "proposals": [
                    {
                        "id": row["id"],
                        "status": row.get("status"),
                        "statement": row.get("statement"),
                    }
                    for row in rows
                ]
            }
        )
    finally:
        hub.close()


def proposals_decide(data_dir: str, proposal_id: str, *, accept: bool) -> None:
    hub = _hub(data_dir)
    try:
        _print(hub.decide_proposal(proposal_id, accept))
    finally:
        hub.close()


def link_mint(data_dir: str, name: str) -> None:
    hub = _hub(data_dir)
    try:
        _print(hub.mint_link(name))
    finally:
        hub.close()


def connections_list(data_dir: str) -> None:
    hub = _hub(data_dir)
    try:
        _print(
            {
                "connections": [
                    {
                        "id": row["id"],
                        "name": row.get("name"),
                        "status": row.get("status"),
                    }
                    for row in hub.connections()
                ]
            }
        )
    finally:
        hub.close()


def grant_create(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        selectors = {"project": args.project} if args.project else None
        stored = hub.create_grant(args.connection, args.preset, None, selectors)
        _print({"id": stored["id"], "summary_human": stored.get("summary_human")})
    finally:
        hub.close()


def connection_revoke(data_dir: str, connection_id: str) -> None:
    hub = _hub(data_dir)
    try:
        stored = hub.revoke_connection(connection_id)
        _print({"id": stored["id"], "status": stored.get("status")})
    finally:
        hub.close()


def import_memories(data_dir: str, args) -> None:
    hub = _hub(data_dir)
    try:
        try:
            result = import_vendor_file(hub, Path(args.src), provider=args.provider)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        _print(result)
    finally:
        hub.close()
