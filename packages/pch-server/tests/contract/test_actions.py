def test_action_routes_are_not_mounted(client):
    response = client.post(
        "/v1/actions/intents",
        json={
            "kind": "send_message",
            "summary_human": "email Jane",
            "payload": {},
            "basis_refs": [],
            "idempotency_key": "abc",
        },
    )
    assert response.status_code == 404
