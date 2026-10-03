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
    visa = client.post(
        "/v1/projects",
        json={"title": "Visa renewal", "charter": "Renew travel visa", "status": "active"},
    ).json()
    work = client.post(
        "/v1/projects",
        json={"title": "Work Roadmap", "charter": "Q3 delivery", "status": "active"},
    ).json()
    client.post(
        "/v1/relations",
        json={"from_id": trip["id"], "to_id": visa["id"], "relation_type": "depends_on"},
    )
    client.post(
        "/v1/relations",
        json={"from_id": work["id"], "to_id": trip["id"], "relation_type": "related_to"},
    )
    return trip, visa, work


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
def test_work_scope_omits_personal_relations(client):
    trip, visa, work = _seed_world(client)
    worker = _agent(client, "work", work["id"])
    body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json={"purpose": "continue the work roadmap"},
    ).json()
    assert body.get("relations") == []
    dumped = str(body)
    assert "depends_on" not in dumped
    assert "blocked_by" not in dumped
    assert "related_to" not in dumped
    assert "Europe" not in dumped
    assert "Visa renewal" not in dumped
    assert trip["id"] not in dumped
    assert visa["id"] not in dumped
    for note in body.get("omissions") or []:
        assert "id" not in note
        assert set(note) <= {"category", "label", "count"}
        assert "Europe" not in note.get("label", "")
        assert trip["id"] not in note.get("label", "")
        assert visa["id"] not in note.get("label", "")
