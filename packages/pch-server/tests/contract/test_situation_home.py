from __future__ import annotations


def test_owner_situation_empty_vault(client):
    res = client.get("/v1/situation")
    assert res.status_code == 200
    assert res.json() == {"project": None, "contract": None}


def test_owner_situation_anchors_seeded_trip(client):
    created = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two.",
            "status": "active",
            "operational_phase": "deciding",
            "situation_intent": "choose the city",
        },
    )
    assert created.status_code == 200
    pid = created.json()["id"]
    client.post(
        "/v1/goals",
        json={"title": "Plan 10-day trip for two", "status": "open", "project_id": pid},
    )
    res = client.get("/v1/situation")
    assert res.status_code == 200
    body = res.json()
    assert body["project"]["id"] == pid
    assert body["contract"]["situation"]["title"] == "Europe Trip"
    assert body["contract"]["situation"]["operational_phase"] == "deciding"
    assert body["contract"]["purpose"] == "what matters now"


def test_situation_rejects_connection_token(client):
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    token = client.post("/v1/connections/pair", json={"code": link["code"]}).json()["token"]
    res = client.get("/v1/situation", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in (401, 403)
