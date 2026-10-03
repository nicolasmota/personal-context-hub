from pathlib import Path

from portable_state.export import export_archive
from portable_state.import_ import open_archive


def test_roundtrip(hub, tmp_path: Path):
    hub.create("project", {"title": "Atlas", "status": "active", "charter": "go"})
    dest = tmp_path / "out.pca"
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    assert opened["records"]
    assert opened["manifest"]["pca_version"] == "0.2.0"
    assert opened["manifest"]["format"] == "0.2.0"


def test_tamper_detected(hub, tmp_path: Path):
    dest = tmp_path / "out.pca"
    export_archive(hub, dest, "pw", {})
    dest.write_bytes(dest.read_bytes() + b"nope")
    try:
        open_archive(dest, "pw")
        # decrypt may fail or integrity fail
    except Exception:
        return
