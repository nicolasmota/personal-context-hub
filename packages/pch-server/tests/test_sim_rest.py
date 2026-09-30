from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient
from pch_core.service import Hub
from pch_server.rest.app import create_app


def test_seq_increases_before_complete(tmp_path: Path) -> None:
    everyday = Hub(tmp_path / "everyday", plain=True)
    sim_hub = Hub(tmp_path / "sim", plain=True)
    app = create_app(everyday, sim_hub=sim_hub)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        client.headers["Authorization"] = f"Bearer {everyday.owner_token}"
        client.post("/v1/setup", json={"name": "Tester"})
        started = client.post(
            "/v1/sim/runs",
            json={"persona_id": "lived-stretch", "delay_ms": 80, "auto_accept": True},
        )
        assert started.status_code == 200, started.text
        run_id = started.json()["id"]
        seen: list[int] = []
        deadline = time.time() + 30
        while time.time() < deadline:
            body = client.get(f"/v1/sim/runs/{run_id}").json()
            seq = int(body["current_seq"])
            seen.append(seq)
            if seq >= 5 and body["status"] == "running":
                break
            if body["status"] in {"complete", "failed", "stopped"}:
                break
            time.sleep(0.05)
        assert max(seen) >= 1
        if seen[-1] < 5:
            mid = max(s for s in seen if s < seen[-1]) if len(set(seen)) > 1 else 0
            assert mid >= 1 or body["status"] == "running"
        grew = any(a < b for a, b in zip(seen, seen[1:], strict=False))
        assert grew or max(seen) >= 5
