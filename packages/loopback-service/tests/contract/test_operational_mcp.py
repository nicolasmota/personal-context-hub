def test_operational_proposal_tool_is_not_mounted(client):
    response = client.post(
        "/v1/mcp/tools/propose_operational_state",
        json={"target_id": "missing", "operational_phase": "planning"},
    )
    assert response.status_code == 404
    assert client.get("/v1/operational-proposals").status_code == 404
