from pathlib import Path

from fastapi.testclient import TestClient
from loopback_service.rest.app import create_app
from trust_kernel.service import Hub


def test_http_does_not_disclose_the_owner_token(tmp_path: Path):
    hub = Hub(tmp_path, plain=True)
    app = create_app(hub)
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    bootstrap = client.get("/v1/bootstrap")
    assert bootstrap.status_code == 200
    assert "owner_token" not in bootstrap.text
    assert bootstrap.json()["owner_credential"] == "owner.token"
    created = client.post("/v1/setup", json={"name": "Ada"})
    assert created.status_code == 200
    assert "owner_token" not in created.text
    credential = tmp_path / "owner.token"
    assert credential.read_text(encoding="utf-8") == hub.owner_token
    assert credential.stat().st_mode & 0o777 == 0o600
    foreign = client.get("/v1/bootstrap", headers={"Host": "evil.example"})
    assert foreign.status_code == 421
    cross_origin = client.get("/v1/bootstrap", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {key.lower() for key in cross_origin.headers}
