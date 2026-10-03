import pytest


def _seed_world(client):
    trip = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two",
            "status": "active",
            "classification": "personal",
        },
    ).json()
    work = client.post(
        "/v1/projects",
        json={"title": "Work Roadmap", "charter": "Q3 delivery", "status": "active"},
    ).json()
    return trip, work


def _agent(client, name, project_id):
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


@pytest.mark.forbidden_context
def test_work_scope_new_runtime_omits_personal_trip(client):
    trip, work = _seed_world(client)
    worker = _agent(client, "hermes", work["id"])
    body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json={"purpose": "continue the work roadmap"},
    ).json()
    dumped = str(body)
    assert "Europe" not in dumped
    assert trip["id"] not in dumped
    situation = body.get("situation")
    if situation:
        assert situation.get("project_id") != trip["id"]
        assert "Europe" not in (situation.get("title") or "")
    for note in body.get("omissions") or []:
        assert "id" not in note
        assert set(note) <= {"category", "label", "count"}
        assert trip["id"] not in note.get("label", "")
