import json
from pathlib import Path

import pytest
from pch_archive.export import export_archive
from pch_archive.import_ import open_archive
from pch_archive.vendor.validate import validate_pam_store, validate_ump_records

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"


def test_empty_export_writes_pam_and_ump(hub, tmp_path: Path):
    dest = tmp_path / "empty.pca"
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    zf = opened["zip"]
    pam = json.loads(zf.read("interoperability/pam/memory-store.json"))
    ump = json.loads(zf.read("interoperability/ump/memories.ump.json"))
    validate_pam_store(pam)
    validate_ump_records(ump)
    assert pam["exported_by"].startswith("personal-context-hub/")
    assert isinstance(ump, list)


def test_full_export_keeps_pam_and_ump_aligned(hub, tmp_path: Path):
    a = hub.create("project", {"title": "A", "status": "active"})
    b = hub.create("project", {"title": "B", "status": "active"})
    ma = hub.create(
        "memory",
        {"statement": "alpha fact", "kind": "semantic", "project_id": a["id"]},
    )
    hub.create(
        "memory",
        {"statement": "beta fact", "kind": "semantic", "project_id": b["id"]},
    )
    dest = tmp_path / "f.pca"
    with pytest.raises(ValueError, match="selective"):
        export_archive(hub, dest, "pw", {"projects": [a["id"]]})
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    zf = opened["zip"]
    pca_mem_ids = {r["id"] for r in opened["records"] if r.get("type") == "memory"}
    pam = json.loads(zf.read("interoperability/pam/memory-store.json"))
    ump = json.loads(zf.read("interoperability/ump/memories.ump.json"))
    pam_ids = {m["id"] for m in pam["memories"] if m.get("id", "").startswith("mem_")}
    ump_ids = {
        rec["id"].removeprefix("urn:ump:") for rec in ump if rec["id"].startswith("urn:ump:mem_")
    }
    assert ma["id"] in pca_mem_ids
    assert pca_mem_ids == pam_ids == ump_ids
    validate_pam_store(pam)
    validate_ump_records(ump)
