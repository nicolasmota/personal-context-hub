def test_revoke_invalidates(client):
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    agent = {"Authorization": f"Bearer {pair['token']}"}
    client.post(f"/v1/connections/{pair['connection_id']}/revoke")
    r = client.get("/v1/search", params={"q": "x", "purpose": "p"}, headers=agent)
    assert r.status_code == 401
