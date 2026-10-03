import io
import zipfile
from pathlib import Path

import pytest
from pch_archive.export import _decrypt, _encrypt, export_archive
from pch_archive.import_ import IntegrityError, import_archive
from pch_core.service import Hub


def test_round_trip_keeps_receipts_rules_and_blocks(hub, tmp_path: Path):
    evidence = hub.record_evidence(
        kind="user_confirmed",
        source="person",
        authority_label="person",
        observed_at="2026-09-01T00:00:00Z",
        statement="Lives in Lisbon",
    )
    hub.evolve(subject="city", value="Lisbon", reason="stated", evidence_ids=[evidence["id"]])
    hub.get_context_contract("owner", "continue the trip")
    hub.save_auto_rule("city")
    hub.withhold_category("health")
    paired = hub.pair(hub.mint_link("reader")["code"])
    hub.create_grant(paired["connection_id"], None, ["project.read"], None)
    hub.set_state("scratch", {"note": "temporary"}, 60, "private_to_connection", "owner")
    dest = tmp_path / "remainder.pca"
    export_archive(hub, dest, "pw")
    other = Hub(tmp_path / "imported", plain=True)
    other.setup("Imported")
    import_archive(other, dest, "pw")
    assert other.list("disclosure_receipt")
    assert other.list("auto_rule")
    assert other.list("disclosure_block")
    assert not other.list("connection")
    assert not other.list("shared_state")
    kept = next(row for row in other.list("evidence") if row["id"] == evidence["id"])
    assert kept["kind"] == "user_confirmed"
    other.close()


def test_stale_hash_writes_nothing(hub, tmp_path: Path):
    hub.evolve(subject="city", value="Lisbon", reason="stated", evidence_ids=[])
    dest = tmp_path / "clean.pca"
    export_archive(hub, dest, "pw")
    raw = _decrypt(dest.read_bytes(), "pw")
    source = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as rewritten:
        for name in source.namelist():
            data = source.read(name)
            if name == "objects/preferences.jsonl":
                data = data.replace(b"Lisbon", b"Porto")
            rewritten.writestr(name, data)
    tampered = tmp_path / "tampered.pca"
    tampered.write_bytes(_encrypt(out.getvalue(), "pw"))
    other = Hub(tmp_path / "empty", plain=True)
    other.setup("Empty")
    before = [row["id"] for row in other.store.list()]
    with pytest.raises(IntegrityError):
        import_archive(other, tampered, "pw")
    assert [row["id"] for row in other.store.list()] == before
    other.close()
