def _pair(client, name: str) -> dict:
    link = client.post("/v1/connections/links", json={"name": name}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    client.post(
        "/v1/grants",
        json={
            "connection_id": pair["connection_id"],
            "capabilities": ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
            "classification_ceiling": "private",
        },
    )
    return pair


def _seed_trip_visa(client):
    trip = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two. Candidates: Amsterdam and London.",
            "status": "active",
        },
    ).json()
    visa = client.post(
        "/v1/projects",
        json={"title": "Visa renewal", "charter": "Renew travel visa", "status": "active"},
    ).json()
    return trip, visa


def test_two_agents_agree(client):
    trip, visa = _seed_trip_visa(client)
    client.post(
        "/v1/relations",
        json={"from_id": trip["id"], "to_id": visa["id"], "relation_type": "depends_on"},
    )
    one = _pair(client, "cursor")
    two = _pair(client, "hermes")
    purpose = {"purpose": "continue planning the trip"}
    a = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {one['token']}"},
        json=purpose,
    ).json()
    b = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {two['token']}"},
        json=purpose,
    ).json()

    def keys(contract):
        return sorted(
            (row["relation_type"], row["from"]["id"], row["to"]["id"]) for row in contract["relations"]
        )

    assert ("depends_on", trip["id"], visa["id"]) in keys(a)
    assert keys(a) == keys(b)


def test_propose_does_not_write_until_accept(client):
    trip, visa = _seed_trip_visa(client)
    agent = _pair(client, "cursor")
    proposed = client.post(
        "/v1/mcp/tools/propose_relation",
        headers={"Authorization": f"Bearer {agent['token']}"},
        json={"from_id": trip["id"], "to_id": visa["id"], "relation_type": "related_to"},
    )
    assert proposed.status_code == 200
    body = proposed.json()
    assert body["status"] == "pending"
    assert body["type"] == "relation_proposal"
    live = client.get("/v1/relations").json()
    assert live == []
    pending = client.get("/v1/relation-proposals?status=pending").json()
    assert any(row["id"] == body["id"] for row in pending)
    accepted = client.post(f"/v1/relation-proposals/{body['id']}/accept")
    assert accepted.status_code == 200
    live = client.get("/v1/relations").json()
    assert any(row["relation_type"] == "related_to" for row in live)
    again = client.post(
        "/v1/mcp/tools/propose_relation",
        headers={"Authorization": f"Bearer {agent['token']}"},
        json={"from_id": visa["id"], "to_id": trip["id"], "relation_type": "related_to"},
    ).json()
    rejected = client.post(f"/v1/relation-proposals/{again['id']}/reject")
    assert rejected.status_code == 200
    live = client.get("/v1/relations").json()
    assert not any(row["from_id"] == visa["id"] and row["to_id"] == trip["id"] for row in live)
    conflict = client.post(f"/v1/relation-proposals/{again['id']}/accept")
    assert conflict.status_code == 409
