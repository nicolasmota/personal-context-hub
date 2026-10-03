from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from portable_state.export import _decrypt


class IntegrityError(ValueError):
    pass


class UnsupportedArchive(ValueError):
    pass


SUPPORTED_VERSIONS = {"0.2.0", "0.1.0"}
FORMAT_020_MEMBERS = (
    "experiences.json",
    "evidence.json",
    "transitions.json",
    "state_conflicts.json",
    "relations.json",
    "grants.json",
    "versions.json",
)


def open_archive(path: Path, passphrase: str) -> dict[str, Any]:
    raw = _decrypt(path.read_bytes(), passphrase)
    zf = zipfile.ZipFile(io.BytesIO(raw))
    manifest = json.loads(zf.read("manifest.json"))
    files = manifest.get("integrity", {}).get("files", {})
    for rel, expected in files.items():
        data = zf.read(rel)
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise IntegrityError(f"hash mismatch for {rel}")
    records: list[dict] = []
    for name in zf.namelist():
        if (
            name.startswith("objects/")
            and name.endswith(".jsonl")
            and not name.endswith("versions.jsonl")
        ):
            text = zf.read(name).decode()
            for line in text.splitlines():
                if line.strip():
                    records.append(json.loads(line))
    versions = []
    if "objects/versions.jsonl" in zf.namelist():
        for line in zf.read("objects/versions.jsonl").decode().splitlines():
            if line.strip():
                versions.append(json.loads(line))
    return {"manifest": manifest, "records": records, "versions": versions, "zip": zf}


def archive_version(manifest: dict[str, Any]) -> str:
    if manifest.get("format"):
        return str(manifest["format"])
    legacy = str(manifest.get("pca_version") or "")
    if legacy == "0.1.0":
        return "0.1.0"
    return ""


def _validate_020(opened: dict[str, Any]) -> None:
    zf = opened["zip"]
    names = set(zf.namelist())
    for member in FORMAT_020_MEMBERS:
        if member not in names:
            raise IntegrityError(f"missing {member}")
        payload = json.loads(zf.read(member))
        if not isinstance(payload, list):
            raise IntegrityError(f"{member} must be a list")
    for row in opened["records"]:
        if not row.get("id") or not row.get("type"):
            raise IntegrityError("archive record is missing id or type")


def import_archive(hub, path: Path, passphrase: str) -> dict[str, Any]:
    opened = open_archive(path, passphrase)
    version = archive_version(opened["manifest"])
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedArchive(f"unsupported archive version {version or 'missing'}")
    if version == "0.2.0":
        _validate_020(opened)
    records = list(opened["records"])
    with hub.engine.tx():
        for row in records:
            if row.get("type") in {"shared_state", "connection"}:
                continue
            hub.store.put(dict(row), new=True)
    return {
        "format": "0.2.0" if version == "0.2.0" else version,
        "migrated_from": version,
        "count": len(records),
    }
