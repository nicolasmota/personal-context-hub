from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trust_kernel.timeutil import now_iso

_MEMORY_NAMES = ("memories.json", "memory.json")
_TEXT_SUFFIXES = {".txt", ".md"}


@dataclass(frozen=True)
class ImportedMemory:
    statement: str
    source: str
    external_id: str | None = None
    observed_at: str | None = None


def import_vendor_file(hub: Any, path: Path, *, provider: str | None = None) -> dict[str, Any]:
    filename, payload = _read_payload(path)
    entries = parse_vendor_payload(payload, filename=filename, provider=provider)
    return apply_import(hub, entries, provider=provider or _sniff(payload, filename))


def parse_vendor_payload(
    payload: Any,
    *,
    filename: str,
    provider: str | None = None,
) -> list[ImportedMemory]:
    if isinstance(payload, str):
        source = provider or "pasted"
        return _from_text(payload, source)
    chosen = provider or _sniff(payload, filename)
    if chosen == "claude":
        return _from_claude(payload)
    if chosen == "chatgpt":
        return _from_chatgpt(payload)
    raise ValueError(
        "unrecognised memory export; pass --provider chatgpt or claude, "
        "or a memories.json / memory.json file"
    )


def apply_import(hub: Any, entries: list[ImportedMemory], *, provider: str) -> dict[str, Any]:
    origin = f"origin:{provider}"
    evidence = hub.record_evidence(
        kind="source_fact",
        source=provider,
        authority_label=provider,
        observed_at=now_iso(),
        statement=f"Imported {len(entries)} memories from {provider}. Text is untrusted data.",
        confidence=0.5,
        verification_status="unverified",
        provenance_chain=[provider],
    )
    created: list[str] = []
    skipped = 0
    for entry in entries:
        statement = entry.statement.strip()
        if not statement:
            skipped += 1
            continue
        if _already(hub, statement, origin):
            skipped += 1
            continue
        labels = [origin, "untrusted"]
        if entry.external_id:
            labels.append(f"external:{entry.external_id}")
        row = hub.create(
            "memory",
            {
                "statement": statement,
                "kind": "semantic",
                "authority": "source_imported",
                "confidence": 0.5,
                "labels": labels,
                "untrusted": True,
                "source_refs": [evidence["id"]],
                "created_at": entry.observed_at,
            },
        )
        created.append(row["id"])
    return {
        "provider": provider,
        "imported": len(created),
        "skipped": skipped,
        "ids": created,
        "evidence_id": evidence["id"],
    }


def _already(hub: Any, statement: str, origin: str) -> bool:
    for row in hub.list("memory"):
        if row.get("statement") == statement and origin in (row.get("labels") or []):
            return True
    return False


def _read_payload(path: Path) -> tuple[str, Any]:
    if not path.is_file():
        raise ValueError(f"import source not found: {path}")
    if path.suffix.lower() == ".zip":
        return _read_zip(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in _TEXT_SUFFIXES:
        return path.name, text
    try:
        return path.name, json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("import source is not JSON or a memory text file") from exc


def _read_zip(path: Path) -> tuple[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if not name.endswith("/") and Path(name).name in _MEMORY_NAMES
        ]
        if not names:
            raise ValueError(
                "export zip has no memory.json or memories.json; chat transcripts are not imported"
            )
        names.sort(key=lambda name: (Path(name).name != "memories.json", name))
        chosen = names[0]
        raw = archive.read(chosen)
    return Path(chosen).name, json.loads(raw.decode("utf-8"))


def _sniff(payload: Any, filename: str) -> str:
    if filename == "memories.json":
        return "claude"
    if filename == "memory.json":
        return "chatgpt"
    if isinstance(payload, dict) and (
        "conversations_memory" in payload
        or "memory_files" in payload
        or "project_memories" in payload
    ):
        return "claude"
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        row = payload[0]
        if "conversations_memory" in row or "memory_files" in row or "project_memories" in row:
            return "claude"
        if any(key in row for key in ("content", "text", "memory")):
            return "chatgpt"
    raise ValueError("could not tell chatgpt from claude; pass --provider")


def _from_text(text: str, source: str) -> list[ImportedMemory]:
    entries: list[ImportedMemory] = []
    for line in text.splitlines():
        statement = line.strip()
        if not statement or statement.startswith("#"):
            continue
        entries.append(ImportedMemory(statement=statement, source=source))
    return entries


def _from_chatgpt(payload: Any) -> list[ImportedMemory]:
    rows = payload if isinstance(payload, list) else [payload]
    entries: list[ImportedMemory] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("enabled") is False:
            continue
        statement = _text(row, "content", "text", "memory")
        if not statement:
            continue
        entries.append(
            ImportedMemory(
                statement=statement,
                source="chatgpt",
                external_id=_optional_str(row.get("id")),
                observed_at=_optional_str(row.get("created_at") or row.get("updated_at")),
            )
        )
    return entries


def _from_claude(payload: Any) -> list[ImportedMemory]:
    rows: list[Any]
    if isinstance(payload, list):
        rows = payload
    else:
        rows = [payload]
    entries: list[ImportedMemory] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        modelled = False
        prose = row.get("conversations_memory")
        if isinstance(prose, str) and prose.strip():
            modelled = True
            entries.append(
                ImportedMemory(
                    statement=prose.strip(), source="claude", external_id="conversations_memory"
                )
            )
        for item in row.get("memory_files") or []:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            content = item.get("content")
            if not isinstance(path, str) or not isinstance(content, str) or not content.strip():
                continue
            modelled = True
            entries.append(
                ImportedMemory(
                    statement=content.strip(),
                    source="claude",
                    external_id=path,
                    observed_at=_optional_str(item.get("created_at") or item.get("updated_at")),
                )
            )
        projects = row.get("project_memories")
        if isinstance(projects, dict):
            for key, value in projects.items():
                if isinstance(value, str) and value.strip():
                    modelled = True
                    entries.append(
                        ImportedMemory(
                            statement=value.strip(),
                            source="claude",
                            external_id=str(key),
                        )
                    )
        if modelled:
            continue
        statement = _text(row, "content", "memory", "text")
        if statement:
            entries.append(
                ImportedMemory(
                    statement=statement,
                    source="claude",
                    external_id=_optional_str(row.get("uuid") or row.get("id")),
                )
            )
    return entries


def _text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
