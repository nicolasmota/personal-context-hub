def test_mcp_context_tools(client):
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    prj = client.post("/v1/projects", json={"title": "Atlas", "charter": "c", "status": "active"}).json()
    client.post("/v1/grants", json={"connection_id": pair["connection_id"], "preset": "read_project", "selectors": {"project": prj["id"]}})
    agent = {"Authorization": f"Bearer {pair['token']}"}
    res = client.post(
        "/v1/mcp/tools/search_personal_context",
        headers=agent,
        json={"query": "Atlas", "purpose": "brief", "scope": {"project": prj["id"]}},
    )
    assert res.status_code == 200
    man = client.post(
        "/v1/mcp/tools/get_context_manifest",
        headers=agent,
        json={"purpose": "brief", "requested_capabilities": ["project.read"], "selectors": {"project": prj["id"]}},
    )
    assert man.status_code == 200
