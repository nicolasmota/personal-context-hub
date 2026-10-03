def test_financial_never_auto_accept(client):
    link = client.post("/v1/connections/links", json={"name": "a"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    agent = {"Authorization": f"Bearer {pair['token']}"}
    r = client.post(
        "/v1/mcp/tools/propose_memory",
        headers=agent,
        json={
            "memory": {"statement": "salary is X", "kind": "semantic", "sensitivity_flags": ["financial"]},
            "evidence_refs": ["art_1"],
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] != "auto_accepted"
