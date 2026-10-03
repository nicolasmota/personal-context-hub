def test_every_write_has_event(client):
    client.post("/v1/projects", json={"title": "X", "status": "active"})
    events = client.get("/v1/events").json()
    assert events
    assert client.get("/v1/events/verify").json()["ok"] is True
