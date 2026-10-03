from trust_kernel.errors import PolicyDenied


def test_same_explanation_on_hub_http_and_resource(client):
    hub = client.app.state.hub
    evidence = hub.record_evidence(
        kind="user_confirmed",
        source="person",
        authority_label="person",
        observed_at="2026-09-01T00:00:00Z",
        statement="Lives in Lisbon",
    )
    hub.evolve(subject="city", value="Lisbon", reason="stated", evidence_ids=[evidence["id"]])
    direct = hub.explain_subject("city")
    http = client.post("/v1/mcp/tools/explain_subject", json={"subject": "city"})
    assert http.status_code == 200
    via_tool = client.app.state.mcp.call("explain_subject", "owner", subject="city")
    resource = client.app.state.mcp.resource("personal-context://explain?subject=city", "owner")
    assert direct["value"] == http.json()["value"] == via_tool["value"] == resource["value"] == "Lisbon"
    before = [row["id"] for row in hub.store.list()]
    refused = client.post("/v1/mcp/tools/read_everything", json={})
    assert refused.status_code == 403
    vault = client.get("/v1/mcp/resources", params={"uri": "personal-context://vault"})
    assert vault.status_code == 403
    assert [row["id"] for row in hub.store.list()] == before
    try:
        client.app.state.mcp.resource("personal-context://vault", "owner")
    except PolicyDenied:
        pass
    else:
        raise AssertionError("personal-context://vault was served")


def test_five_tools_match_on_http(client):
    hub = client.app.state.hub
    evidence = hub.record_evidence(
        kind="user_confirmed",
        source="person",
        authority_label="person",
        observed_at="2026-09-01T00:00:00Z",
        statement="Lives in Lisbon",
    )
    hub.evolve(subject="city", value="Lisbon", reason="stated", evidence_ids=[evidence["id"]])
    project = hub.create("project", {"title": "Trip", "status": "active"})
    link = client.post("/v1/connections/links", json={"name": "reader"}).json()
    paired = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    grant = hub.create_grant(
        paired["connection_id"],
        None,
        ["project.read", "memory.retrieve", "profile.read"],
        {"project": project["id"]},
    )
    proposal = hub.propose_memory(
        {"statement": "also Lisbon", "kind": "semantic"},
        paired["connection_id"],
        [evidence["id"]],
    )
    impact = hub.source_impact(evidence["id"])
    http_impact = client.post("/v1/mcp/tools/source_impact", json={"evidence_id": evidence["id"]})
    resource = client.app.state.mcp.resource(f"personal-context://impact?evidence={evidence['id']}", "owner")
    assert http_impact.status_code == 200
    http_ids = {item["id"] for item in http_impact.json()["live_facts"]}
    assert http_ids == {item["id"] for item in impact["live_facts"]}
    assert {item["id"] for item in resource["live_facts"]} == http_ids
    owner_status = client.post("/v1/mcp/tools/proposal_status", json={})
    assert any(row["id"] == proposal["id"] for row in owner_status.json()["proposals"])
    recipient = {"Authorization": f"Bearer {paired['token']}"}
    own = client.post("/v1/mcp/tools/proposal_status", json={}, headers=recipient)
    assert [row["id"] for row in own.json()["proposals"]] == [proposal["id"]]
    contract = hub.get_context_contract(
        paired["connection_id"], "continue the trip", subject_ref=project["id"]
    )
    requested = client.post(
        "/v1/mcp/tools/request_action",
        json={
            "kind": "send",
            "summary": "send the note",
            "contract_id": contract["contract_id"],
            "idempotency_key": "door-1",
        },
        headers=recipient,
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "pending"
    direct = hub.propose_action(
        paired["connection_id"],
        "send",
        "send the note",
        {},
        [],
        "door-2",
        contract["contract_id"],
    )
    assert direct["status"] == "pending"
    revoked = client.post(
        "/v1/mcp/tools/revoke_my_grant",
        json={"grant_id": grant["id"]},
        headers=recipient,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    nxt = client.post(
        "/v1/mcp/tools/get_context_contract",
        json={"purpose": "continue the trip", "subject_ref": project["id"]},
        headers=recipient,
    )
    assert nxt.status_code == 403
    assert "Lisbon" not in nxt.text
