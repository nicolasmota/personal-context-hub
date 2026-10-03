from pathlib import Path

from portable_state.export import export_archive
from portable_state.import_ import open_archive


def test_plugin_secret_excluded_from_export(hub, tmp_path: Path):
    secret = "plugin-super-secret"
    hub._kv_set("plugin_secret:demo:oauth", secret)
    dest = tmp_path / "space.pca"
    export_archive(hub, dest, "pw")
    opened = open_archive(dest, "pw")
    blob = str(opened["records"]) + str(opened["manifest"]) + str(opened["versions"])
    assert secret not in blob
    assert "plugin_secret:" not in blob
    assert hub._kv_get("plugin_secret:demo:oauth") == secret
