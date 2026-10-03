from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pch_core.errors import PclError
from pch_core.ids import new_id
from pch_core.schema.audit import EventKind
from pch_core.service import Hub
from pch_core.timeutil import now_iso
from pydantic import BaseModel

from pch_server.rest.auth import get_hub, require_owner

router = APIRouter(tags=["portability"])


class ExportBody(BaseModel):
    passphrase: str
    filters: dict = {}


class StageBody(BaseModel):
    path: str
    passphrase: str


class ApplyBody(BaseModel):
    resolutions: list[dict] = []


class VendorImportBody(BaseModel):
    path: str


class ArchiveBody(BaseModel):
    admit: bool


@router.post("/export")
def export(body: ExportBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    from pch_archive.export import export_archive

    dest = hub.data_dir / "exports" / f"space-{now_iso().replace(':', '')}.pca"
    result = export_archive(hub, dest, body.passphrase, body.filters)
    hub.ledger.append(EventKind.EXPORT_CREATED, "owner", "export created", extra=result)
    hub.engine.conn.commit()
    return result


@router.post("/import/stage")
def stage(body: StageBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    from pch_archive.import_ import open_archive
    from pch_archive.resolve import plan_resolutions
    from pch_archive.untrusted import mark_untrusted

    try:
        opened = open_archive(Path(body.path), body.passphrase)
    except Exception as exc:
        raise PclError("not_pca", "Not a Portable Context Archive", 400) from exc
    records = [mark_untrusted(r) for r in opened["records"]]
    existing = {r["id"]: r for t in ("memory", "project", "goal") for r in hub.list(t)}
    for t in ("commitment", "decision", "preference", "artifact", "profile", "person"):
        for r in hub.list(t):
            existing[r["id"]] = r
    plan = plan_resolutions(records, set(existing), existing)
    staging_id = new_id("import_staging")
    payload = {
        "id": staging_id,
        "type": "import_staging",
        "archive_manifest": opened["manifest"],
        "records": records,
        "conflicts": [p for p in plan if p["action"] == "conflict"],
        "item_resolutions": plan,
        "status": "staged",
        "space_id": "personal",
        "owner": hub.person_id(),
        "labels": [],
        "classification": "private",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source_refs": [],
        "confidence": 1.0,
        "authority": "source_imported",
        "retention": {"mode": "until_revoked"},
        "policy_tags": [],
        "version": 1,
    }
    with hub.engine.tx():
        hub.store.put(payload)
        hub.ledger.append(EventKind.IMPORT_STAGED, "owner", "import staged", [staging_id])
    return payload


@router.get("/import/staging/{staging_id}")
def get_staging(staging_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)) -> dict:
    return hub.get(staging_id)


@router.post("/import/staging/{staging_id}/apply")
def apply(
    staging_id: str, body: ApplyBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    from pch_archive.resolve import apply_resolution

    staging = hub.get(staging_id)
    choices = {r.get("id"): r.get("action", "merge") for r in body.resolutions}
    applied = 0
    with hub.engine.tx():
        for item in staging.get("item_resolutions") or []:
            action = choices.get(item["id"], item["action"])
            if action in ("skip", "conflict"):
                if action == "conflict":
                    continue
                continue
            rec = apply_resolution(action if action != "create" else "merge", item["record"])
            rec["authority"] = rec.get("authority") or "source_imported"
            hub.store.put(rec)
            applied += 1
        staging["status"] = "applied"
        hub.store.put(staging)
        hub.ledger.append(EventKind.IMPORT_APPLIED, "owner", f"imported {applied}", [staging_id])
    return {"applied": applied, "staging_id": staging_id}


@router.post("/import/vendor")
def vendor_import(
    body: VendorImportBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    from pch_archive.vendor.enqueue import enqueue_vendor_import

    return enqueue_vendor_import(hub, Path(body.path))


@router.get("/import/vendor/{batch_id}")
def get_vendor_batch(
    batch_id: str, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    row = hub.get(batch_id)
    if row.get("type") != "vendor_import_batch":
        raise PclError("not_found", "vendor import batch not found", 404)
    return row


@router.post("/import/vendor/{batch_id}/archive")
def vendor_archive(
    batch_id: str, body: ArchiveBody, hub: Hub = Depends(get_hub), _o: str = Depends(require_owner)
) -> dict:
    from pch_archive.vendor.enqueue import decide_archive

    return decide_archive(hub, batch_id, body.admit)
