import pytest


def _seed_world(client):
    trip = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two",
            "status": "active",
            "classification": "personal",
            "operational_phase": "deciding",
            "current_step": "rank two remaining itineraries",
            "situation_intent": "choose next itinerary",
        },
    ).json()
    work = client.post(
        "/v1/projects",
        json={
            "title": "Work Roadmap",
            "charter": "Q3 delivery",
            "status": "active",
            "operational_phase": "planning",
            "situation_intent": "ship the quarterly plan",
        },
    ).json()
    client.post(
        "/v1/memories",
        json={
            "statement": "Amsterdam is a live destination candidate",
            "kind": "semantic",
            "project_id": trip["id"],
            "classification": "personal",
        },
    )
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
def test_work_scope_omits_personal_phase(client):
    trip, work = _seed_world(client)
    worker = _agent(client, "work", work["id"])
    body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json={"purpose": "continue the work roadmap"},
    ).json()
    situation = body.get("situation")
    if situation:
        assert situation.get("operational_phase") != "deciding"
        assert situation.get("situation_intent") != "choose next itinerary"
        assert situation.get("project_id") != trip["id"]
        assert "Europe" not in (situation.get("title") or "")
    for candidate in body.get("candidates") or []:
        assert candidate.get("operational_phase") != "deciding"
        assert "Europe" not in (candidate.get("title") or "")
        assert candidate.get("project_id") != trip["id"]
    dumped = str(body)
    assert "choose next itinerary" not in dumped
    assert trip["id"] not in dumped
    for note in body.get("omissions") or []:
        assert "id" not in note
        assert set(note) <= {"category", "label", "count"}
        assert "Europe" not in note.get("label", "")
        assert trip["id"] not in note.get("label", "")
