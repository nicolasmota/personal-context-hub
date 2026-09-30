def _pair(client, name: str, project_id: str) -> dict:
    link = client.post("/v1/connections/links", json={"name": name}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    client.post(
        "/v1/grants",
        json={
            "connection_id": pair["connection_id"],
            "capabilities": ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
            "selectors": {"project": project_id},
            "classification_ceiling": "private",
        },
    )
    return pair


def _seed_trip(client):
    prj = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two. Candidates: Amsterdam and London.",
            "status": "active",
            "operational_phase": "deciding",
        },
    ).json()
    client.post(
        "/v1/goals",
        json={"title": "Plan 10-day trip for two", "status": "open", "project_id": prj["id"]},
    )
    return prj


def test_two_real_use_runtimes_agree(client):
    trip = _seed_trip(client)
    hermes = _pair(client, "hermes", trip["id"])
    claw = _pair(client, "openclaw", trip["id"])
    purpose = {"purpose": "continue planning the trip"}
    a = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {hermes['token']}"},
        json=purpose,
    ).json()
    b = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {claw['token']}"},
        json=purpose,
    ).json()
    assert a["situation"]["project_id"] == trip["id"]
    assert a["situation"]["project_id"] == b["situation"]["project_id"]
    assert {g["ref"]["id"] for g in a["goals"]} == {g["ref"]["id"] for g in b["goals"]}
    assert a["situation"].get("operational_phase") == b["situation"].get("operational_phase")


def test_switch_runtime_keeps_trip(client):
    trip = _seed_trip(client)
    first = _pair(client, "cursor", trip["id"])
    before = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {first['token']}"},
        json={"purpose": "continue planning the trip"},
    ).json()
    assert before["situation"]["project_id"] == trip["id"]
    second = _pair(client, "hermes", trip["id"])
    after = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {second['token']}"},
        json={"purpose": "continue planning the trip"},
    ).json()
    assert after["situation"]["project_id"] == trip["id"]
    assert after["situation"]["title"] == "Europe Trip"


def test_revoke_does_not_delete_hub_objects(client):
    trip = _seed_trip(client)
    agent = _pair(client, "hermes", trip["id"])
    client.post(f"/v1/connections/{agent['connection_id']}/revoke")
    listed = client.get("/v1/projects").json()
    assert any(row["id"] == trip["id"] for row in listed)
    live = client.get(f"/v1/projects/{trip['id']}").json()
    assert live["title"] == "Europe Trip"
    assert live.get("operational_phase") == "deciding"
    denied = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {agent['token']}"},
        json={"purpose": "continue planning the trip"},
    )
    assert denied.status_code in (401, 403)
