def test_proposals(client):
    link = client.post("/v1/connections/links", json={"name": "a"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    agent = {"Authorization": f"Bearer {pair['token']}"}
    r = client.post(
        "/v1/memories/proposals",
        headers=agent,
        json={"memory": {"statement": "likes tea", "kind": "semantic", "sensitivity_flags": []}, "evidence_refs": ["art_1"]},
    )
    assert r.status_code == 200
    pid = r.json()["id"]
    acc = client.post(f"/v1/memories/proposals/{pid}/accept", json={})
    assert acc.status_code == 200
