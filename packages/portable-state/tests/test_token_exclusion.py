from pathlib import Path

from portable_state.export import export_archive
from portable_state.import_ import open_archive


def test_connector_token_excluded_from_export(hub, tmp_path: Path):
    secret = "super-secret-refresh-token"
    hub._kv_set("connector_token:demo", secret)
    dest = tmp_path / "space.pca"
    export_archive(hub, dest, "pw")
    opened = open_archive(dest, "pw")
    blob = str(opened["records"]) + str(opened["manifest"]) + str(opened["versions"])
    assert secret not in blob
    assert "connector_token:" not in blob
    assert hub._kv_get("connector_token:demo") == secret
