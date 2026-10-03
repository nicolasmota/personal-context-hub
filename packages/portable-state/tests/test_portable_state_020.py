import io
import json
import zipfile
from pathlib import Path

import pytest
from portable_state.export import _decrypt, _encrypt, export_archive
from portable_state.import_ import UnsupportedArchive, import_archive
from trust_kernel.service import Hub


def _rewrite(path: Path, passphrase: str, version: str) -> None:
    raw = _decrypt(path.read_bytes(), passphrase)
    src = zipfile.ZipFile(io.BytesIO(raw))
    manifest = json.loads(src.read("manifest.json"))
    manifest["format"] = version
    manifest["pca_version"] = version
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "manifest.json":
                data = json.dumps(manifest).encode()
            zf.writestr(info.filename, data)
    path.write_bytes(_encrypt(buf.getvalue(), passphrase))


def test_round_trip_keeps_experience_and_grants(hub, tmp_path: Path):
    hub.create("preference", {"key": "food.spicy", "value": "hot"})
    hub.capture_experience(
        action="noted dinner",
        operating_context="home",
        outcome="recorded",
        occurred_at="2026-09-29T12:00:00Z",
        provenance="owner",
    )
    link = hub.mint_link("guest")
    paired = hub.pair(link["code"], runtime_info={"harness": "test"})
    hub.create_grant(
        paired["connection_id"],
        None,
        ["project.read"],
        {},
        "private",
    )
    dest = tmp_path / "state.pca"
    export_archive(hub, dest, "pw")
    other = Hub(tmp_path / "empty", plain=True)
    try:
        imported = import_archive(other, dest, "pw")
        assert imported["format"] == "0.2.0"
        prefs = [row for row in other.list("preference") if row.get("key") == "food.spicy"]
        assert prefs and prefs[0]["value"] == "hot"
        assert other.list("experience")
        assert other.list("grant")
    finally:
        other.close()


def test_previous_version_migrates(hub, tmp_path: Path):
    hub.create("preference", {"key": "city", "value": "Lisbon"})
    dest = tmp_path / "old.pca"
    export_archive(hub, dest, "pw")
    _rewrite(dest, "pw", "0.1.0")
    other = Hub(tmp_path / "migrated", plain=True)
    try:
        imported = import_archive(other, dest, "pw")
        assert imported["migrated_from"] == "0.1.0"
        assert any(row.get("value") == "Lisbon" for row in other.list("preference"))
    finally:
        other.close()


def test_unsupported_version_leaves_destination_unchanged(hub, tmp_path: Path):
    hub.create("preference", {"key": "city", "value": "Lisbon"})
    dest = tmp_path / "future.pca"
    export_archive(hub, dest, "pw")
    _rewrite(dest, "pw", "9.9.9")
    other = Hub(tmp_path / "dest", plain=True)
    try:
        with pytest.raises(UnsupportedArchive):
            import_archive(other, dest, "pw")
        assert other.list("preference") == []
    finally:
        other.close()


def test_subset_filter_is_refused(hub, tmp_path: Path):
    with pytest.raises(ValueError, match="selective"):
        export_archive(hub, tmp_path / "no.pca", "pw", {"ids": ["x"]})
    assert not (tmp_path / "no.pca").exists()
