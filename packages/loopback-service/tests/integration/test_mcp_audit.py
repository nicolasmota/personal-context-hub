def test_mcp_calls_are_audited(client):
    link = client.post("/v1/connections/links", json={"name": "a"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    agent = {"Authorization": f"Bearer {pair['token']}"}
    client.post("/v1/mcp/tools/search_personal_context", headers=agent, json={"query": "x", "purpose": "p"})
    events = client.get("/v1/events").json()
    assert any(e.get("actor") == pair["connection_id"] for e in events)
