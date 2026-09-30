from __future__ import annotations

import json
from pathlib import Path

from pch_archive.export import export_archive
from pch_archive.import_ import IntegrityError, UnsupportedArchive, import_archive
from pch_core.errors import ValidationFailed
from pch_core.service import OWNER, Hub


def _print(payload: dict) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _hub(data_dir: str) -> Hub:
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return Hub(path, plain=True)


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
