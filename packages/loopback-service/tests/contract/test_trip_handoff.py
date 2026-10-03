def _seed_trip(client):
    prj = client.post(
        "/v1/projects",
        json={
            "title": "Europe Trip",
            "charter": "Plan a 10-day travel trip for two. Candidates: Amsterdam and London.",
            "status": "active",
        },
    ).json()
    pid = prj["id"]
    client.post(
        "/v1/goals", json={"title": "Plan 10-day trip for two", "status": "open", "project_id": pid}
    )
    client.post(
        "/v1/preferences",
        json={"key": "travel.budget", "value": "budget-sensitive", "project_id": pid},
    )
    client.post(
        "/v1/memories",
        json={
            "statement": "Two travelers planning a 10-day Europe trip",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    client.post(
        "/v1/memories",
        json={
            "statement": "Amsterdam is a live destination candidate",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    client.post(
        "/v1/memories",
        json={
            "statement": "London is a destination candidate",
            "kind": "semantic",
            "project_id": pid,
        },
    )
    client.post(
        "/v1/decisions",
        json={
            "title": "Destination shortlist",
            "chosen_option": "",
            "alternatives": ["Amsterdam", "London"],
            "project_id": pid,
        },
    )
    client.post(
        "/v1/commitments",
        json={"title": "Stay within travel budget", "status": "open", "project_id": pid},
    )
    return prj


def _pair_with_trip_grant(client, name: str, project_id: str) -> dict:
    link = client.post("/v1/connections/links", json={"name": name}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    client.post(
        "/v1/grants",
        json={
            "connection_id": pair["connection_id"],
            "capabilities": ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
            "selectors": {"project": project_id},
            "classification_ceiling": "private",
        },
    )
    return pair


def _substance(body: dict) -> dict:
    def refs(section: str) -> list[tuple]:
        return sorted(
            (item["ref"]["id"], item["ref"]["type"], item["ref"]["summary"])
            for item in body[section]
        )

    return {
        "situation": body["situation"]["project_id"] if body["situation"] else None,
        "goals": refs("goals"),
        "preferences": refs("preferences"),
        "memories": refs("memories"),
        "decisions": refs("decisions"),
        "constraints": refs("constraints"),
    }


def test_two_agents_same_package_without_search(client):
    prj = _seed_trip(client)
    one = _pair_with_trip_grant(client, "cursor", prj["id"])
    two = _pair_with_trip_grant(client, "hermes", prj["id"])
    purpose = {"purpose": "continue planning the trip"}
    a = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {one['token']}"},
        json=purpose,
    )
    b = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers={"Authorization": f"Bearer {two['token']}"},
        json=purpose,
    )
    assert a.status_code == 200 and b.status_code == 200
    body_a, body_b = a.json(), b.json()
    assert _substance(body_a) == _substance(body_b)
    assert any("10-day" in g["body"].get("title", "") for g in body_a["goals"])
    assert any(p["body"].get("key") == "travel.budget" for p in body_a["preferences"])
    assert any(
        "two travelers" in (m["body"].get("statement") or "").lower() for m in body_a["memories"]
    )
    assert any(
        "Amsterdam"
        in ((d["body"].get("chosen_option") or "") + " ".join(d["body"].get("alternatives") or []))
        for d in body_a["decisions"]
    )
    for item in body_a["goals"] + body_a["memories"] + body_a["decisions"] + body_a["preferences"]:
        assert item["citation"]
    search_events = client.get("/v1/events", params={"kind": "context.request"}).json()
    assert search_events == []


def test_dropped_london_propagates(client):
    prj = _seed_trip(client)
    agent = _pair_with_trip_grant(client, "cursor", prj["id"])
    headers = {"Authorization": f"Bearer {agent['token']}"}
    client.post(
        "/v1/decisions",
        json={
            "title": "Dropped London",
            "chosen_option": "Amsterdam",
            "alternatives": ["London"],
            "rationale": "Person dropped London",
            "status": "rejected",
            "project_id": prj["id"],
        },
    )
    body = client.post(
        "/v1/mcp/tools/get_context_contract",
        headers=headers,
        json={"purpose": "continue planning the trip"},
    ).json()
    titles = [d["body"].get("title") for d in body["decisions"]]
    assert "Dropped London" in titles
    assert any(d["body"].get("chosen_option") == "Amsterdam" for d in body["decisions"])
    assert not any(d["body"].get("chosen_option") == "London" for d in body["decisions"])
