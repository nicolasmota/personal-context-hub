import pytest


@pytest.mark.forbidden_context
def test_cannot_read_other_project(client):
    a = client.post("/v1/projects", json={"title": "Atlas", "status": "active"}).json()
    b = client.post("/v1/projects", json={"title": "Finance", "status": "active"}).json()
    client.post("/v1/memories", json={"statement": "secret finance", "kind": "semantic", "project_id": b["id"], "classification": "sensitive"})
    client.post("/v1/memories", json={"statement": "atlas note", "kind": "semantic", "project_id": a["id"]})
    link = client.post("/v1/connections/links", json={"name": "demo"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    client.post("/v1/grants", json={"connection_id": pair["connection_id"], "preset": "read_project", "selectors": {"project": a["id"]}})
    agent = {"Authorization": f"Bearer {pair['token']}"}
    res = client.get("/v1/search", params={"q": "secret", "purpose": "snoop"}, headers=agent)
    ids = [r["id"] for r in res.json().get("results", [])]
    statements = [r.get("statement") for r in res.json().get("results", [])]
    assert "secret finance" not in statements
    assert all(r.get("project_id") != b["id"] for r in res.json().get("results", []))
    assert ids is not None
