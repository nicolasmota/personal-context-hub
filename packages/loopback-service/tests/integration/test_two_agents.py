def test_two_agents_same_brief(client):
    prj = client.post("/v1/projects", json={"title": "Atlas", "charter": "one", "status": "active"}).json()
    agents = []
    for name in ("one", "two"):
        link = client.post("/v1/connections/links", json={"name": name}).json()
        pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
        client.post("/v1/grants", json={"connection_id": pair["connection_id"], "preset": "read_project", "selectors": {"project": prj["id"]}})
        agents.append(pair)
    h1 = {"Authorization": f"Bearer {agents[0]['token']}"}
    h2 = {"Authorization": f"Bearer {agents[1]['token']}"}
    b1 = client.get(f"/v1/projects/{prj['id']}/brief", headers=h1).json()
    b2 = client.get(f"/v1/projects/{prj['id']}/brief", headers=h2).json()
    assert b1["project"]["id"] == b2["project"]["id"]
    assert b1["versions"] == b2["versions"]
