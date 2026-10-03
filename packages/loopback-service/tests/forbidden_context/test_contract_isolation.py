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
    client.post(
        "/v1/memories",
        json={
            "statement": "Amsterdam is a live destination candidate",
            "kind": "semantic",
            "project_id": trip["id"],
            "classification": "personal",
        },
    )
    client.post(
        "/v1/memories",
        json={
            "statement": "Ship the Q3 roadmap this week",
            "kind": "semantic",
            "project_id": work["id"],
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
def test_zero_cross_scope_leakage(client):
    trip, work = _seed_world(client)
    personal = _agent(client, "personal", trip["id"])
    worker = _agent(client, "work", work["id"])
    purpose = {"purpose": "schedule around my travel"}
    p_body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {personal['token']}"},
        json=purpose,
    ).json()
    w_body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json=purpose,
    ).json()
    p_ids = {
        i["ref"]["id"]
        for sec in ("goals", "memories", "decisions", "preferences")
        for i in p_body[sec]
    }
    w_ids = {
        i["ref"]["id"]
        for sec in ("goals", "memories", "decisions", "preferences")
        for i in w_body[sec]
    }
    assert not (p_ids & w_ids)
    assert all(
        "Amsterdam" not in (i["body"].get("statement") or "")
        for sec in ("memories",)
        for i in w_body[sec]
    )
    if w_body["omissions"]:
        for note in w_body["omissions"]:
            assert "id" not in note
            assert set(note) <= {"category", "label", "count"}
            assert "Amsterdam" not in note["label"]


@pytest.mark.forbidden_context
def test_revoked_connection_refuses_and_audits(client):
    trip, _work = _seed_world(client)
    agent = _agent(client, "cursor", trip["id"])
    client.post(f"/v1/connections/{agent['connection_id']}/revoke")
    res = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {agent['token']}"},
        json={"purpose": "continue planning the trip"},
    )
    assert res.status_code in (401, 403)
    events = client.get("/v1/events", params={"kind": "context.contract"}).json()
    assert any(e.get("extra", {}).get("status") == "refused" for e in events)


@pytest.mark.forbidden_context
def test_historical_personal_preference_does_not_leak(client):
    trip, work = _seed_world(client)
    pref = client.post(
        "/v1/preferences",
        json={
            "key": "food.spicy",
            "value": "dislike",
            "project_id": trip["id"],
            "classification": "personal",
        },
    ).json()
    superseded = client.post(
        f"/v1/preferences/{pref['id']}/supersede",
        json={"value": "like"},
    ).json()
    worker = _agent(client, "work", work["id"])
    w_body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json={"purpose": "schedule around my travel"},
    ).json()
    w_ids = {
        i["ref"]["id"]
        for sec in ("goals", "memories", "decisions", "preferences")
        for i in w_body[sec]
    }
    w_ids |= {r["id"] for r in w_body.get("references") or []}
    assert pref["id"] not in w_ids
    assert superseded["successor"]["id"] not in w_ids
    for note in w_body["omissions"]:
        assert "id" not in note
        assert pref["id"] not in note.get("label", "")


@pytest.mark.forbidden_context
def test_work_incident_does_not_see_northwind_offer(client):
    incident = client.post(
        "/v1/projects",
        json={
            "title": "Checkout incident",
            "charter": "Restore checkout. Monday deadline for the token and deploy.",
            "status": "active",
        },
    ).json()
    offer = client.post(
        "/v1/projects",
        json={
            "title": "Northwind offer",
            "charter": "Staff engineer loop at Northwind. Monday deadline for the token and deploy.",
            "status": "active",
            "classification": "personal",
        },
    ).json()
    client.post(
        "/v1/decisions",
        json={
            "title": "Incident mitigation",
            "chosen_option": "rollback v2.4",
            "alternatives": ["forward-fix"],
            "project_id": incident["id"],
        },
    )
    client.post(
        "/v1/decisions",
        json={
            "title": "Employer loop",
            "chosen_option": "Northwind",
            "alternatives": ["Contoso"],
            "project_id": offer["id"],
        },
    )
    worker = _agent(client, "incident-work", incident["id"])
    work_body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {worker['token']}"},
        json={"purpose": "continue the incident"},
    ).json()
    assert work_body["situation"]["project_id"] == incident["id"]
    dumped = str(work_body)
    assert "Northwind" not in dumped
    assert offer["id"] not in dumped
    for note in work_body.get("omissions") or []:
        assert set(note) <= {"category", "label", "count"}
        assert "Northwind" not in note["label"]
        assert "id" not in note
