def test_contract_issuance_appears_in_events(client):
    client.post("/v1/projects", json={"title": "Europe Trip", "charter": "trip", "status": "active"})
    res = client.post("/v1/mcp/tools/get_context_contract", json={"purpose": "continue planning the trip"})
    assert res.status_code == 200
    body = res.json()
    events = client.get("/v1/events", params={"kind": "context.contract"}).json()
    assert events
    extra = events[-1].get("extra") or {}
    assert extra.get("contract_id") == body["contract_id"]
    assert extra.get("purpose") == "continue planning the trip"
    assert extra.get("status") == "issued"
    assert "item_refs" in extra
    assert "omission_categories" in extra
