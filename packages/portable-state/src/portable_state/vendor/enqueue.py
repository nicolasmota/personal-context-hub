from __future__ import annotations

import hashlib
from pathlib import Path

from pch_core.errors import PclError, ValidationFailed, VersionConflict
from pch_core.ids import new_id
from pch_core.schema.audit import EventKind
from pch_core.schema.proposal import ProposalStatus
from pch_core.service import Hub
from pch_core.timeutil import now_iso

from pch_archive.vendor.conversations import list_conversations
from pch_archive.vendor.detect import detect_source
from pch_archive.vendor.map_structured import map_structured

ACTORS = {
    "chatgpt": "importer.chatgpt",
    "claude": "importer.claude",
    "gemini": "importer.gemini",
    "pam": "importer.pam",
    "ump": "importer.ump",
}


def origin_label(source: str, original_id: str) -> str:
    return f"origin:{source}:{original_id}"


def fingerprint(source: str, original_id: str) -> str:
    return hashlib.sha256(f"{source}:{original_id}".encode()).hexdigest()


def _existing_origins(hub: Hub) -> set[str]:
    found: set[str] = set()
    for row in hub.list("proposal") + hub.list("memory"):
        mem = row.get("proposed_memory") if row.get("type") == "proposal" else row
        for lab in (mem or {}).get("labels") or []:
            if str(lab).startswith("origin:"):
                found.add(str(lab))
    return found


def _batch_payload(hub: Hub, batch: dict) -> dict:
    now = now_iso()
    payload = {
        **batch,
        "type": "vendor_import_batch",
        "space_id": "personal",
        "owner": hub.person_id(),
        "labels": [],
        "classification": "private",
        "updated_at": now,
        "created_at": batch.get("created_at") or now,
        "source_refs": [],
        "confidence": 1.0,
        "authority": "source_imported",
        "retention": {"mode": "until_revoked"},
        "policy_tags": [],
        "version": 1,
    }
    return payload


def enqueue_vendor_import(hub: Hub, path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise ValidationFailed("import path not found")
    source = detect_source(path)
    if source == "unknown":
        raise PclError(
            "unrecognized_layout",
            "Not a known ChatGPT, Claude, Gemini, PAM, or UMP layout",
            400,
        )
    structured = map_structured(path, source)
    conversations = list_conversations(path, source)
    origins = _existing_origins(hub)
    proposal_ids: list[str] = []
    skipped: list[str] = []
    items: list[dict] = []
    actor = ACTORS[source]
    created = now_iso()
    batch_id = new_id("vendor_import_batch")
    with hub.engine.tx():
        for obj in structured:
            label = origin_label(source, obj["original_id"])
            fp = fingerprint(source, obj["original_id"])
            preview = obj["statement"][:120]
            if label in origins:
                skipped.append(fp)
                items.append(
                    {
                        "fingerprint": fp,
                        "original_id": obj["original_id"],
                        "proposal_id": None,
                        "statement_preview": preview,
                    }
                )
                continue
            kinds = {"semantic", "episodic", "procedural", "summary"}
            kind = obj["kind"] if obj["kind"] in kinds else "semantic"
            proposed = hub.propose_memory(
                {
                    "statement": obj["statement"],
                    "kind": kind,
                    "labels": [label, f"vendor:{source}"],
                    "authority": "proposed",
                },
                actor,
                [batch_id],
            )
            if proposed.get("status") == ProposalStatus.AUTO_ACCEPTED:
                proposed["status"] = ProposalStatus.PENDING
                proposed["policy_verdict"] = "needs_review"
                hub.store.put(proposed)
            origins.add(label)
            proposal_ids.append(proposed["id"])
            items.append(
                {
                    "fingerprint": fp,
                    "original_id": obj["original_id"],
                    "proposal_id": proposed["id"],
                    "statement_preview": preview,
                }
            )
        archive_status = "pending" if conversations else "none"
        batch = {
            "id": batch_id,
            "source": source,
            "path_basename": path.name,
            "status": "complete" if archive_status == "none" else "enqueued",
            "archive_status": archive_status,
            "memory_item_count": len(structured),
            "conversation_count": len(conversations),
            "proposal_ids": proposal_ids,
            "skipped_fingerprints": skipped,
            "items": items,
            "conversation_stubs": conversations,
            "created_at": created,
        }
        hub.store.put(_batch_payload(hub, batch))
        hub.ledger.append(
            EventKind.IMPORT_VENDOR_ENQUEUED,
            actor,
            "vendor import enqueued",
            [batch_id],
        )
    return {
        "id": batch_id,
        "source": source,
        "memory_item_count": len(structured),
        "conversation_count": len(conversations),
        "enqueued": len(proposal_ids),
        "skipped": len(skipped),
        "archive_status": archive_status,
        "proposal_ids": proposal_ids,
    }


def decide_archive(hub: Hub, batch_id: str, admit: bool) -> dict:
    batch = hub.get(batch_id)
    if batch.get("type") != "vendor_import_batch":
        raise ValidationFailed("not a vendor import batch")
    current = batch.get("archive_status")
    if current in {"admitted", "discarded"}:
        raise VersionConflict("archive already decided")
    if current == "none":
        raise ValidationFailed("this import has no conversation archive")
    source = batch["source"]
    stubs = batch.get("conversation_stubs") or []
    with hub.engine.tx():
        if admit:
            for stub in stubs:
                now = now_iso()
                hub.store.put(
                    {
                        "id": new_id("artifact"),
                        "space_id": "personal",
                        "type": "artifact",
                        "kind": "conversation",
                        "title": stub.get("title") or stub.get("original_id") or "conversation",
                        "body": stub.get("body") or "",
                        "body_text": stub.get("body") or "",
                        "untrusted": True,
                        "owner": hub.person_id(),
                        "labels": [origin_label(source, str(stub.get("original_id") or ""))],
                        "classification": "private",
                        "created_at": now,
                        "updated_at": now,
                        "source_refs": [batch_id],
                        "confidence": 1.0,
                        "authority": "source_imported",
                        "retention": {"mode": "until_revoked"},
                        "policy_tags": [],
                        "version": 1,
                    }
                )
            batch["archive_status"] = "admitted"
        else:
            batch["archive_status"] = "discarded"
        batch["status"] = "complete"
        hub.store.put(batch)
        hub.ledger.append(
            EventKind.IMPORT_ARCHIVE_DECIDED,
            "owner",
            "conversation archive decided",
            [batch_id],
            extra={"admit": admit},
        )
    return batch
