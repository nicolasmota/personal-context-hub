from pathlib import Path

from fastapi.testclient import TestClient
from pch_core.service import Hub
from pch_server.rest.app import create_app


def test_existing_vault_reused_by_packaged_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PCH_PLAIN_SQLITE", "1")
    source = tmp_path / "vault"
    hub = Hub(source, plain=True)
    hub.setup("Owner")
    created = hub.create("project", {"title": "Atlas", "charter": "keep", "status": "active"})
    obj_id = created["id"]
    hub.close()
    app = create_app(Hub(source, plain=True))
    with TestClient(app) as client:
        boot = client.get("/v1/bootstrap").json()
        client.headers["Authorization"] = f"Bearer {boot['owner_token']}"
        got = client.get(f"/v1/projects/{obj_id}")
        assert got.status_code == 200
        assert got.json()["id"] == obj_id
        assert got.json()["title"] == "Atlas"
    extras = [p for p in tmp_path.iterdir() if p != source]
    assert extras == []
