import sys
from pathlib import Path

from pch_server.pairing.catalog import render_recipe


def test_catalog_and_recipe(client):
    listed = client.get("/v1/catalog/assistants")
    assert listed.status_code == 200
    ids = [a["id"] for a in listed.json()]
    assert "cursor" in ids
    link = client.post("/v1/connections/links", json={"name": "cursor"}).json()
    recipe = client.post(
        f"/v1/connections/{link['connection_id']}/recipe",
        json={"assistant": "cursor"},
    )
    assert recipe.status_code == 200
    body = recipe.json()
    assert "pch_sdk" in str(body["snippet"])
    assert body["snippet"]["mcpServers"]["personal-context-hub"]["env"]["PCH_TOKEN"]
    events = client.get("/v1/events").json()
    assert any(e.get("kind") == "connection.recipe_issued" for e in events)
    bad = client.post(
        f"/v1/connections/{link['connection_id']}/recipe",
        json={"assistant": "not-a-real-agent"},
    )
    assert bad.status_code == 422


def test_catalog_lists_hermes_and_openclaw(client):
    listed = client.get("/v1/catalog/assistants")
    assert listed.status_code == 200
    by_id = {row["id"]: row for row in listed.json()}
    assert by_id["cursor"]["supported"] is True
    assert by_id["hermes"]["supported"] is True
    assert by_id["openclaw"]["supported"] is True
    assert "demo-agent" not in by_id


def test_catalog_cursor_and_hermes_are_validated(client):
    listed = client.get("/v1/catalog/assistants")
    assert listed.status_code == 200
    by_id = {row["id"]: row for row in listed.json()}
    assert by_id["cursor"]["validated"] is True
    assert by_id["hermes"]["validated"] is True
    for assistant_id in ("openclaw", "claude-code", "claude-desktop", "chatgpt"):
        assert by_id[assistant_id]["supported"] is True
        assert by_id[assistant_id]["validated"] is False


def test_hermes_and_openclaw_recipes(client):
    link = client.post("/v1/connections/links", json={"name": "runtime"}).json()
    conn = link["connection_id"]
    hermes = client.post(f"/v1/connections/{conn}/recipe", json={"assistant": "hermes"})
    assert hermes.status_code == 200
    h = hermes.json()
    assert h["format"] == "hermes-yaml"
    env = h["snippet"]["mcp_servers"]["personal-context-hub"]["env"]
    assert env["PCH_TOKEN"]
    assert env["PCH_BASE"] == "http://127.0.0.1:8765"
    assert "pch_sdk" in str(h["snippet"])
    assert "mcp_servers" in h["instructions"] or "hermes" in h["instructions"].lower()
    claw = client.post(f"/v1/connections/{conn}/recipe", json={"assistant": "openclaw"})
    assert claw.status_code == 200
    c = claw.json()
    assert c["format"] == "openclaw-json"
    claw_env = c["snippet"]["mcp"]["servers"]["personal-context-hub"]["env"]
    assert claw_env["PCH_BASE"] == "http://127.0.0.1:8765"
    assert "127.0.0.1" in claw_env["PCH_BASE"]


def test_unknown_assistant_recipe_rejected(client):
    link = client.post("/v1/connections/links", json={"name": "runtime"}).json()
    bad = client.post(
        f"/v1/connections/{link['connection_id']}/recipe",
        json={"assistant": "not-a-real-agent"},
    )
    assert bad.status_code == 422


def _recipe(client, assistant: str) -> dict:
    link = client.post("/v1/connections/links", json={"name": assistant}).json()
    response = client.post(
        f"/v1/connections/{link['connection_id']}/recipe",
        json={"assistant": assistant},
    )
    assert response.status_code == 200
    return response.json()


def test_cursor_recipe_is_person_level_not_project_only(client):
    body = _recipe(client, "cursor")
    instructions = body["instructions"].lower()
    assert "every window" in instructions or (
        "settings" in instructions and "mcp" in instructions
    )
    assert body["instructions"] != "Add this to .cursor/mcp.json, then reload MCP servers."
    assert "only supported" not in instructions
    assert "user" in instructions or "settings" in instructions


def test_recipes_include_copyable_runtime_rule(client):
    for assistant in ("cursor", "hermes", "openclaw"):
        body = _recipe(client, assistant)
        rule = (body.get("runtime_rule") or "").lower()
        assert rule
        assert "task start" in rule or "situation" in rule
        assert "propose" in rule
        assert "invent" in rule
        assert "canonical" in rule or "live truth" in rule or "not live" in rule


def test_bridge_uses_installed_interpreter():
    body = render_recipe("cursor", "tok", "http://127.0.0.1:18765")
    bridge = body["snippet"]["mcpServers"]["personal-context-hub"]
    command = Path(bridge["command"])
    assert command.is_absolute()
    assert command.exists()
    assert "uv run" not in " ".join([bridge["command"], *bridge["args"]])
    assert bridge["args"] == ["-m", "pch_sdk", "mcp-bridge"]
    assert bridge["env"]["PCH_BASE"] == "http://127.0.0.1:18765"
    assert bridge["command"] == sys.executable


