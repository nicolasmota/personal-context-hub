import json
from pathlib import Path

from pch_archive.export import export_archive
from pch_archive.import_ import open_archive
from pch_archive.vendor.enqueue import enqueue_vendor_import

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"

FORBIDDEN = ("refresh_token", "client_secret", "pairing", "grant_")


def test_export_omits_pending_proposals_and_secrets(hub, tmp_path: Path):
    enqueue_vendor_import(hub, FIXTURES / "claude")
    dest = tmp_path / "h.pca"
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    types = {r.get("type") for r in opened["records"]}
    assert "proposal" not in types
    assert "grant" not in types
    zf = opened["zip"]
    blob = zf.read("interoperability/pam/memory-store.json").decode()
    blob += zf.read("interoperability/ump/memories.ump.json").decode()
    for rec in opened["records"]:
        blob += json.dumps(rec)
    assert "Vegetarian except fish" not in blob
    for token in FORBIDDEN:
        assert token not in blob.lower() or token == "grant_"
    assert "grant" not in types
