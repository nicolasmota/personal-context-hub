from pathlib import Path

from fastapi.testclient import TestClient
from loopback_service.rest.app import create_app
from trust_kernel.service import OWNER, Hub


def _signature(contract: dict) -> dict:
    included = []
    for section in ("goals", "preferences", "memories", "decisions", "constraints", "state"):
        for item in contract.get(section) or []:
            included.append(item["ref"]["id"])
    return {
        "included": sorted(included),
        "sufficient": contract["sufficient"],
        "omissions": sorted((note["category"], note["count"]) for note in contract["omissions"]),
        "conflicts": sorted(
            (note["status"], note["resolution"], note["subject"])
            for note in contract.get("state_conflicts") or []
        ),
        "citations": sorted(
            cite["id"]
            for section in ("goals", "preferences", "memories", "decisions", "constraints", "state")
            for item in contract.get(section) or []
            for cite in item["citation"]
        ),
    }


def test_three_callers_match(tmp_path: Path):
    hub = Hub(tmp_path / "vault", plain=True)
    hub.setup("Tester")
    project = hub.create(
        "project", {"title": "Dinner", "status": "active", "charter": "plan dinner"}
    )
    hub.create("goal", {"title": "plan dinner", "status": "open", "project_id": project["id"]})
    app = create_app(hub)
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    client.headers["Authorization"] = f"Bearer {hub.owner_token}"
    payload = {"purpose": "plan dinner", "subject_ref": project["id"], "max_items": 4}
    direct = hub.get_context_contract(
        OWNER, payload["purpose"], payload["subject_ref"], payload["max_items"]
    )
    http = client.post("/v1/mcp/tools/get_context_contract", json=payload).json()
    tool = app.state.mcp.call("get_context_contract", "owner", **payload)
    assert _signature(direct) == _signature(http) == _signature(tool)
    hub.close()
