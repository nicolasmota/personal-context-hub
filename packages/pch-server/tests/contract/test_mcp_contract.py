REQUIRED = {
    "contract_id",
    "purpose",
    "situation",
    "candidates",
    "goals",
    "preferences",
    "memories",
    "decisions",
    "constraints",
    "state",
    "relations",
    "references",
    "conflicts",
    "granted_scope",
    "omissions",
    "assembled_at",
    "sufficient",
}


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
        "/v1/decisions",
        json={
            "title": "Destination shortlist",
            "chosen_option": "",
            "alternatives": ["Amsterdam", "London"],
            "project_id": pid,
        },
    )
    return prj


def test_empty_purpose_is_422(client):
    res = client.post("/v1/mcp/tools/get_context_contract", json={"purpose": ""})
    assert res.status_code == 422
    events = client.get("/v1/events", params={"kind": "context.contract"}).json()
    assert events == []


def test_invalid_as_of_is_422(client):
    res = client.post(
        "/v1/mcp/tools/get_context_contract", json={"purpose": "plan dinner", "as_of": "not-a-time"}
    )
    assert res.status_code == 422
    events = client.get("/v1/events", params={"kind": "context.contract"}).json()
    assert events == []


def test_no_match_is_200_empty_not_404(client):
    _seed_trip(client)
    res = client.post(
        "/v1/mcp/tools/get_context_contract", json={"purpose": "xyzzy-no-such-situation-zzzz"}
    )
    assert res.status_code == 200
    body = res.json()
    assert set(body) >= REQUIRED
    assert body["situation"] is None
    assert body["goals"] == []
    assert body["memories"] == []
    assert body["granted_scope"]


def test_tie_candidates_not_merged(client):
    client.post(
        "/v1/projects",
        json={"title": "Alpha Trip Planning", "charter": "planning trip", "status": "active"},
    )
    client.post(
        "/v1/projects",
        json={"title": "Beta Trip Planning", "charter": "planning trip", "status": "active"},
    )
    res = client.post("/v1/mcp/tools/get_context_contract", json={"purpose": "planning trip"})
    assert res.status_code == 200
    body = res.json()
    assert body["situation"] is None
    titles = {c["title"] for c in body["candidates"]}
    assert "Alpha Trip Planning" in titles and "Beta Trip Planning" in titles
    assert body["memories"] == []


def test_conflicts_and_determinism(client):
    prj = _seed_trip(client)
    client.post(
        "/v1/preferences",
        json={"key": "flights.red_eye", "value": "avoid", "project_id": prj["id"]},
    )
    other = client.post(
        "/v1/preferences",
        json={"key": "flights.red_eye.alt", "value": "ok-if-cheaper", "project_id": prj["id"]},
    ).json()
    client.patch(f"/v1/preferences/{other['id']}", json={"key": "flights.red_eye"})
    a = client.post(
        "/v1/mcp/tools/get_context_contract", json={"purpose": "continue planning the trip"}
    ).json()
    b = client.post(
        "/v1/mcp/tools/get_context_contract", json={"purpose": "continue planning the trip"}
    ).json()
    assert a["conflicts"]
    a_ids = [item["ref"]["id"] for item in a["preferences"]]
    b_ids = [item["ref"]["id"] for item in b["preferences"]]
    assert a_ids == b_ids
    for item in a["goals"] + a["preferences"] + a["memories"] + a["decisions"]:
        assert item["citation"]


def test_as_of_before_supersede(client):
    _seed_trip(client)
    pref = client.post(
        "/v1/preferences",
        json={"key": "food.spicy", "value": "dislike", "valid_from": "2026-01-01T00:00:00Z"},
    ).json()
    client.post(f"/v1/preferences/{pref['id']}/supersede", json={"value": "like"})
    past = client.post(
        "/v1/mcp/tools/get_context_contract",
        json={"purpose": "continue planning the trip", "as_of": "2026-06-01T00:00:00Z"},
    ).json()
    spicy = [
        p["body"]["value"] for p in past["preferences"] if p["body"].get("key") == "food.spicy"
    ]
    assert "dislike" in spicy
    assert "like" not in spicy


def test_contract_keeps_a_state_list(client):
    _seed_trip(client)
    body = client.post(
        "/v1/mcp/tools/get_context_contract", json={"purpose": "continue planning the trip"}
    ).json()
    assert isinstance(body["state"], list)
    assert "shared_state" not in body
    assert "ActionIntent" not in str(body)
