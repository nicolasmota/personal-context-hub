def test_pairing_and_revoke(client):
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]})
    assert pair.status_code == 200
    token = pair.json()["token"]
    conn_id = pair.json()["connection_id"]
    prj = client.post("/v1/projects", json={"title": "Atlas", "status": "active"}).json()
    client.post("/v1/grants", json={"connection_id": conn_id, "preset": "read_project", "selectors": {"project": prj["id"]}})
    agent = {"Authorization": f"Bearer {token}"}
    bad = client.post("/v1/context-manifests", json={"purpose": "", "requested_capabilities": ["project.read"]}, headers=agent)
    assert bad.status_code in (400, 422)
    client.post(f"/v1/connections/{conn_id}/revoke")
    later = client.get("/v1/search", params={"q": "Atlas", "purpose": "x"}, headers=agent)
    assert later.status_code in (401, 403)
