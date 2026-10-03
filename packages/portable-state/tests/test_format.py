from pathlib import Path

from pch_archive.export import export_archive
from pch_archive.import_ import open_archive


def test_format_opens(hub, tmp_path: Path):
    dest = tmp_path / "x.pca"
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    assert "integrity" in opened["manifest"]
