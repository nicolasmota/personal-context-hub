from pathlib import Path

from pch_archive.export import export_archive
from pch_archive.import_ import open_archive


def test_filter_and_no_secrets(hub, tmp_path: Path):
    hub.create("project", {"title": "A", "status": "active"})
    hub.create("project", {"title": "B", "status": "active"})
    dest = tmp_path / "f.pca"
    try:
        export_archive(hub, dest, "pw", {"projects": ["anything"]})
    except ValueError as exc:
        assert "selective" in str(exc)
    else:
        raise AssertionError("selective export should be refused")
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    types = {r.get("type") for r in opened["records"]}
    assert "connection" not in types
    assert "shared_state" not in types
