from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from loopback_service.rest.app import create_app
from trust_kernel.service import Hub


@pytest.fixture
def client(tmp_path: Path):
    hub = Hub(tmp_path, plain=True)
    app = create_app(hub)
    c = TestClient(app, base_url="http://127.0.0.1:8765")
    c.headers["Authorization"] = f"Bearer {hub.owner_token}"
    c.post("/v1/setup", json={"name": "Tester"})
    return c
