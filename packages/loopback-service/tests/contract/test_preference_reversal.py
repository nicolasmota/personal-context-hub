def _pair(client, name: str, project_id: str) -> dict:
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


def test_two_agents_see_current_like_only(client):
    prj = client.post(
        "/v1/projects",
        json={"title": "Weeknight Dinners", "charter": "Plan dinner this week", "status": "active"},
    ).json()
    pid = prj["id"]
    client.post("/v1/goals", json={"title": "Plan dinner this week", "status": "open", "project_id": pid})
    pref = client.post(
        "/v1/preferences",
        json={"key": "food.spicy", "value": "dislike", "project_id": pid},
    ).json()
    supersede = client.post(
        f"/v1/preferences/{pref['id']}/supersede",
        json={"value": "like", "rationale": "I now like spicy food"},
    )
    assert supersede.status_code == 200
    body = supersede.json()
    assert body["predecessor"]["value"] == "dislike"
    assert body["successor"]["value"] == "like"

    listed = client.get("/v1/preferences").json()
    values = {row["id"]: row for row in listed}
    assert pref["id"] in values
    assert values[pref["id"]]["valid_until"]
    assert body["successor"]["id"] in values

    one = _pair(client, "cursor", pid)
    two = _pair(client, "hermes", pid)
    purpose = {"purpose": "plan dinner this week"}
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

    def live_spicy(contract: dict) -> list:
        return [p["body"]["value"] for p in contract["preferences"] if p["body"].get("key") == "food.spicy"]

    assert live_spicy(a) == ["like"]
    assert live_spicy(b) == ["like"]
    live_ids_a = {p["ref"]["id"] for p in a["preferences"]}
    assert pref["id"] not in live_ids_a
    assert body["successor"]["id"] in live_ids_a
    ref_ids = {r["id"] for r in a["references"]}
    assert pref["id"] not in ref_ids


def test_retract_omitted_from_list_but_get_by_id(client):
    pref = client.post("/v1/preferences", json={"key": "food.cilantro", "value": "hate"}).json()
    retract = client.post(f"/v1/preferences/{pref['id']}/retract")
    assert retract.status_code == 200
    listed = client.get("/v1/preferences").json()
    assert pref["id"] not in {row["id"] for row in listed}
    forensic = client.get(f"/v1/preferences/{pref['id']}")
    assert forensic.status_code == 200
    assert forensic.json()["never_true"] is True
