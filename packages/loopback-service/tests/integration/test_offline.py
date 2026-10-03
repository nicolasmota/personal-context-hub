def test_offline_restart(client, tmp_path):
    client.post("/v1/projects", json={"title": "Atlas", "status": "active"})
    found = client.get("/v1/search", params={"q": "Atlas"})
    assert found.json()["results"]
