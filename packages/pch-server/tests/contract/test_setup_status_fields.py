def test_setup_status_includes_encrypted_and_key_storage(client):
    status = client.get("/v1/setup")
    assert status.status_code == 200
    body = status.json()
    assert isinstance(body["encrypted"], bool)
    assert body["key_storage"] in {"keychain", "file"}


def test_create_app_without_hub_does_not_force_plaintext(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from pch_server.rest.app import create_app

    monkeypatch.delenv("PCH_PLAIN_SQLITE", raising=False)
    app = create_app(data_dir=tmp_path / "vault")
    try:
        assert app.state.hub.engine.encrypted is True
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        assert client.get("/v1/bootstrap").json()["sim_enabled"] is False
    finally:
        app.state.hub.close()


def test_dev_app_sim_disabled_by_default(tmp_path, monkeypatch):
    from pch_server.rest.app import dev_app

    monkeypatch.setenv("PCH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PCH_SIM_DIR", str(tmp_path / "sim"))
    monkeypatch.setenv("PCH_PLAIN_SQLITE", "1")
    monkeypatch.delenv("PCH_SIM_ENABLED", raising=False)
    app = dev_app()
    try:
        assert app.state.sim_enabled is False
    finally:
        app.state.hub.close()
