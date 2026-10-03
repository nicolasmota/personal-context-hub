from __future__ import annotations


def test_owner_capture_starts_situation(client):
    empty = client.get("/v1/situation")
    assert empty.status_code == 200
    assert empty.json() == {"project": None, "contract": None}
    res = client.post(
        "/v1/situation/capture",
        json={"title": "Europe trip", "statement": "ten-day trip for two"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["project"]["title"] == "Europe trip"
    assert body["memory"]["statement"] == "ten-day trip for two"
    assert body["memory"]["authority"] == "user_confirmed"
    assert body["situation"]["project"]["id"] == body["project"]["id"]
    memories = body["situation"]["contract"]["memories"]
    statements = [item["body"]["statement"] for item in memories]
    assert "ten-day trip for two" in statements
    pending = client.get("/v1/memories/proposals?status=pending")
    assert pending.status_code == 200
    assert pending.json() == []


def test_owner_capture_attaches_when_in_play(client):
    client.post(
        "/v1/situation/capture",
        json={"title": "Europe trip", "statement": "ten-day trip for two"},
    )
    res = client.post(
        "/v1/situation/capture",
        json={"statement": "Amsterdam is the live city"},
    )
    assert res.status_code == 200
    statements = [item["body"]["statement"] for item in res.json()["situation"]["contract"]["memories"]]
    assert "ten-day trip for two" in statements
    assert "Amsterdam is the live city" in statements


def test_owner_capture_rejects_incomplete(client):
    res = client.post("/v1/situation/capture", json={"title": "Europe trip", "statement": ""})
    assert res.status_code == 422
    assert client.get("/v1/situation").json() == {"project": None, "contract": None}


def test_situation_capture_rejects_connection_token(client):
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    token = client.post("/v1/connections/pair", json={"code": link["code"]}).json()["token"]
    res = client.post(
        "/v1/situation/capture",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Europe trip", "statement": "ten-day trip for two"},
    )
    assert res.status_code in (401, 403)
