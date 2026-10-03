def test_setup_status_includes_owner_name(client):
    status = client.get("/v1/setup")
    assert status.status_code == 200
    body = status.json()
    assert body["initialized"] is True
    assert body["name"] == "Tester"


def test_setup_and_context(client):
    spaces = client.get("/v1/spaces")
    assert spaces.status_code == 200
    prj = client.post("/v1/projects", json={"title": "Atlas", "charter": "ship it", "status": "active"})
    assert prj.status_code == 200
    pid = prj.json()["id"]
    mem = client.post("/v1/memories", json={"statement": "Atlas uses citations", "kind": "semantic", "project_id": pid})
    assert mem.status_code == 200
    found = client.get("/v1/search", params={"q": "Atlas"})
    assert found.status_code == 200
    assert found.json()["results"]
