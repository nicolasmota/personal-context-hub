from pathlib import Path

from fastapi.testclient import TestClient
from loopback_service.rest.app import create_app
from trust_kernel.service import Hub


def test_ui_routes_survive_refresh(tmp_path: Path):
    hub = Hub(tmp_path, plain=True)
    client = TestClient(create_app(hub), base_url="http://127.0.0.1:8765")
    static = Path(__file__).resolve().parents[2] / "src" / "loopback_service" / "static" / "index.html"
    if not static.is_file():
        return
    for path in ("/connectors", "/projects", "/export", "/connections"):
        res = client.get(path)
        assert res.status_code == 200, path
        assert "html" in res.headers.get("content-type", "")
    api = client.get("/v1/bootstrap")
    assert api.status_code == 200
    assert "owner_token" not in api.json()
