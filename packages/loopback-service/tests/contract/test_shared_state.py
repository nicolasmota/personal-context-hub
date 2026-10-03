def test_shared_state_routes_are_not_mounted(client):
    response = client.put(
        "/v1/state/focus",
        json={"value": "x", "ttl_seconds": 60, "visibility": "private_to_connection"},
    )
    assert response.status_code == 404
