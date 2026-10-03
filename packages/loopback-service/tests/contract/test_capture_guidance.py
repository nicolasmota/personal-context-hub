from pathlib import Path

from pch_sdk.capture_guidance import THREE_TURN_LINES, follow_capture_guidance
from pch_sdk.mcp_bridge import handle_message


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _pair_agent(client):
    link = client.post("/v1/connections/links", json={"name": "capture"}).json()
    pair = client.post("/v1/connections/pair", json={"code": link["code"]}).json()
    client.post(
        "/v1/grants",
        json={
            "connection_id": pair["connection_id"],
            "capabilities": [
                "project.read",
                "commitment.read",
                "memory.retrieve",
                "memory.propose",
                "profile.read",
            ],
            "classification_ceiling": "private",
        },
    )
    return {"Authorization": f"Bearer {pair['token']}"}


def test_three_turn_eval_proposes_not_canonical(client):
    listed = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "http://x", "tok")
    expected = follow_capture_guidance(THREE_TURN_LINES, listed["result"]["tools"])
    assert expected == ["get_context_contract", "propose_memory", "propose_memory"]
    agent = _pair_agent(client)
    purpose = {"purpose": "continue planning the trip"}
    first = client.post("/v1/mcp/tools/get_context_contract", headers=agent, json=purpose)
    assert first.status_code == 200
    facts = THREE_TURN_LINES[1:]
    for statement in facts:
        proposed = client.post(
            "/v1/mcp/tools/propose_memory",
            headers=agent,
            json={
                "memory": {"statement": statement, "kind": "semantic", "sensitivity_flags": []},
                "evidence_refs": ["turn"],
            },
        )
        assert proposed.status_code == 200
        assert proposed.json().get("status") != "accepted"
    live = client.get("/v1/memories").json()
    statements = {item.get("statement") for item in live}
    assert facts[0] not in statements
    assert facts[1] not in statements
    pending = client.get("/v1/memories/proposals?status=pending").json()
    assert len(pending) >= 2
    pid = pending[0]["id"]
    acc = client.post(f"/v1/memories/proposals/{pid}/accept", json={})
    assert acc.status_code == 200
    after = {item.get("statement") for item in client.get("/v1/memories").json()}
    assert facts[0] in after or facts[1] in after


def test_recipe_does_not_write_assistant_config(client, tmp_path, monkeypatch):
    home = tmp_path / "home"
    for name in (".cursor", ".hermes", ".openclaw"):
        (home / name).mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    link = client.post("/v1/connections/links", json={"name": "capture"}).json()
    recipe = client.post(
        f"/v1/connections/{link['connection_id']}/recipe",
        json={"assistant": "cursor"},
    )
    assert recipe.status_code == 200
    assert not (home / ".cursor" / "mcp.json").exists()
    assert list((home / ".cursor").iterdir()) == []
    assert list((home / ".hermes").iterdir()) == []
    assert list((home / ".openclaw").iterdir()) == []


def test_agents_md_still_forbids_hub_client():
    text = (_repo_root() / "AGENTS.md").read_text(encoding="utf-8")
    assert "Do not treat this coding agent as a Hub client" in text
