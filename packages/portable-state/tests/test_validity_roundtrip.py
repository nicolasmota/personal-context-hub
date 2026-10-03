from pathlib import Path

from pch_archive.export import export_archive
from pch_archive.import_ import open_archive


def test_validity_fields_roundtrip(hub, tmp_path: Path):
    hub.create(
        "preference",
        {
            "key": "food.spicy",
            "value": "dislike",
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2026-06-01T00:00:00Z",
            "never_true": False,
        },
    )
    dest = tmp_path / "out.pca"
    export_archive(hub, dest, "pw", {})
    opened = open_archive(dest, "pw")
    prefs = [r for r in opened["records"] if r.get("type") == "preference" and r.get("key") == "food.spicy"]
    assert prefs
    assert prefs[0]["valid_from"] == "2026-01-01T00:00:00Z"
    assert prefs[0]["valid_until"] == "2026-06-01T00:00:00Z"
    assert prefs[0]["never_true"] is False
