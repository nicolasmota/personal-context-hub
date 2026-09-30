from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from pch_core.service import Hub
from pch_core.timeutil import now_iso

from pch_archive.vendor.pam_project import pam_memory_store
from pch_archive.vendor.ump_project import ump_records

PCA_VERSION = "0.2.0"


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _encrypt(data: bytes, passphrase: str) -> bytes:
    try:
        from pyrage import passphrase as age_pass

        return age_pass.encrypt(data, passphrase)
    except Exception:
        import base64
        import os

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return b"PCH1" + salt + Fernet(key).encrypt(data)


def _decrypt(data: bytes, passphrase: str) -> bytes:
    if data.startswith(b"PCH1"):
        import base64

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        salt, rest = data[4:20], data[20:]
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return Fernet(key).decrypt(rest)
    from pyrage import passphrase as age_pass

    return age_pass.decrypt(data, passphrase)


TYPE_FILES = {
    "project": "projects",
    "goal": "goals",
    "commitment": "commitments",
    "decision": "decisions",
    "preference": "preferences",
    "memory": "memories",
    "artifact": "artifacts",
    "profile": "profile",
    "person": "profile",
    "event": "calendar_events",
    "experience": "experiences",
    "evidence": "evidence",
    "state_transition": "transitions",
    "state_conflict": "state_conflicts",
    "relation": "relations",
    "grant": "grants",
}


def export_archive(
    hub: Hub, dest: Path, passphrase: str, filters: dict[str, Any] | None = None
) -> dict:
    filters = filters or {}
    if any(filters.get(key) for key in ("projects", "project", "types", "ids")):
        raise ValueError("selective export is not available")
    buf = io.BytesIO()
    files: dict[str, str] = {}
    grouped: dict[str, list[dict]] = {v: [] for v in set(TYPE_FILES.values())}
    grouped["versions"] = []
    skip_types = {"shared_state", "connection", "manifest", "action_intent", "approval"}
    project_filter = filters.get("projects") or filters.get("project")
    _class_max = filters.get("classification_max")  # reserved for export filter
    for row in hub.store.list():
        if row.get("type") in skip_types:
            continue
        if project_filter:
            pids = project_filter if isinstance(project_filter, list) else [project_filter]
            if row.get("type") == "project" and row["id"] not in pids:
                continue
            if (
                row.get("type") != "project"
                and row.get("project_id") not in pids
                and row.get("id") not in pids
            ):
                continue
        fname = TYPE_FILES.get(row.get("type", ""), None)
        if not fname:
            continue
        grouped[fname].append(row)
        grouped["versions"].extend(hub.versions(row["id"]))
    events = hub.events()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        counts = {}
        for name, items in grouped.items():
            if name == "versions":
                continue
            text = "\n".join(_canonical(i) for i in items)
            path = f"objects/{name}.jsonl"
            zf.writestr(path, text)
            files[path] = hashlib.sha256(text.encode()).hexdigest()
            counts[name] = len(items)
        versions_text = "\n".join(_canonical(i) for i in grouped["versions"])
        zf.writestr("objects/versions.jsonl", versions_text)
        files["objects/versions.jsonl"] = hashlib.sha256(versions_text.encode()).hexdigest()
        root_members = {
            "experiences.json": grouped.get("experiences", []),
            "evidence.json": grouped.get("evidence", []),
            "transitions.json": grouped.get("transitions", []),
            "state_conflicts.json": grouped.get("state_conflicts", []),
            "relations.json": grouped.get("relations", []),
            "grants.json": grouped.get("grants", []),
            "versions.json": grouped["versions"],
        }
        for member, items in root_members.items():
            text = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            zf.writestr(member, text)
            files[member] = hashlib.sha256(text.encode()).hexdigest()
        ev_text = "\n".join(_canonical(e) for e in events)
        zf.writestr("events.jsonl", ev_text)
        files["events.jsonl"] = hashlib.sha256(ev_text.encode()).hexdigest()
        projectable = [
            row for name in ("memories", "preferences", "profile") for row in grouped.get(name, [])
        ]
        pam_doc = pam_memory_store(
            projectable,
            exported_by=f"personal-context-hub/{PCA_VERSION}",
            export_date=now_iso(),
        )
        ump_doc = ump_records(projectable, hub.person_id())
        pam_text = json.dumps(pam_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        ump_text = json.dumps(ump_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        pam_member = "interoperability/pam/memory-store.json"
        ump_member = "interoperability/ump/memories.ump.json"
        zf.writestr(pam_member, pam_text)
        files[pam_member] = hashlib.sha256(pam_text.encode()).hexdigest()
        zf.writestr(ump_member, ump_text)
        files[ump_member] = hashlib.sha256(ump_text.encode()).hexdigest()
        zf.writestr(
            "schemas/memory.schema.json",
            json.dumps({"title": "memory", "type": "object"}),
        )
        manifest = {
            "format": PCA_VERSION,
            "pca_version": PCA_VERSION,
            "created_at": now_iso(),
            "generator": {"name": "personal-context-hub", "version": PCA_VERSION},
            "space": {"id": "personal", "kind": "personal"},
            "filters": filters,
            "counts": counts,
            "integrity": {"algorithm": "sha256", "files": files},
            "schema_migration": {"min_reader_version": "0.1.0"},
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_encrypt(buf.getvalue(), passphrase))
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {
        "path": str(dest),
        "manifest_hash": digest,
        "filters": filters,
        "pca_version": PCA_VERSION,
    }
