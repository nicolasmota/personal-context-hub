import io
import json

import httpx
import pytest
from agent_client.capture_guidance import DURABLE_TRIGGERS, TASK_START_TRIGGERS
from agent_client.mcp_bridge import TOOL_NAMES, handle_message, map_tool_result, run_stdio


def test_tools_list_parity():
    reply = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "http://x", "tok")
    names = [t["name"] for t in reply["result"]["tools"]]
    assert names == TOOL_NAMES
    contract = next(t for t in reply["result"]["tools"] if t["name"] == "get_context_contract")
    assert "as_of" in contract["inputSchema"]["properties"]


def test_revocation_and_unreachable_mapping():
    revoked = map_tool_result(401, {})
    assert "revoked" in revoked["content"][0]["text"].lower()
    assert revoked["isError"] is True
    down = map_tool_result(0, {"detail": "Connection refused"})
    assert (
        "unreachable" in down["content"][0]["text"].lower()
        or "Hub unreachable" in down["content"][0]["text"]
    )


def test_search_round_trip(monkeypatch):
    def fake_call(base, token, name, arguments):
        assert name == "search_personal_context"
        return 200, {"results": [{"id": "mem_1", "statement": "Atlas prefers cited briefs"}]}

    monkeypatch.setattr("agent_client.mcp_bridge.call_hub", fake_call)
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_personal_context",
                "arguments": {"query": "Atlas", "purpose": "brief"},
            },
        },
        "http://x",
        "tok",
    )
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["results"][0]["statement"].startswith("Atlas")


def test_situation_and_propose_descriptions_include_when_to_use():
    reply = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "http://x", "tok")
    tools = {t["name"]: t["description"].lower() for t in reply["result"]["tools"]}
    sit = tools["get_context_contract"]
    prop = tools["propose_memory"]
    assert sit != "get context contract"
    assert prop != "propose memory"
    assert any(token in sit for token in TASK_START_TRIGGERS)
    assert any(token in prop for token in DURABLE_TRIGGERS)
    assert "invent" in sit
    assert "proposal" in prop or "propose" in prop


def test_run_stdio_empty_token_exits(monkeypatch):
    err = io.StringIO()
    monkeypatch.setattr("agent_client.mcp_bridge.sys.stderr", err)
    with pytest.raises(SystemExit) as ei:
        run_stdio("", "http://127.0.0.1:8765")
    assert ei.value.code == 1
    assert "PERSONAL_CONTEXT_TOKEN" in err.getvalue()


def test_run_stdio_hub_down_lists_tools(monkeypatch):
    def fail_health(_base: str) -> None:
        raise httpx.ConnectError("down")

    monkeypatch.setattr("agent_client.mcp_bridge.healthcheck", fail_health)
    monkeypatch.setattr(
        "agent_client.mcp_bridge.sys.stdin",
        io.StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'),
    )
    out = io.StringIO()
    monkeypatch.setattr("agent_client.mcp_bridge.sys.stdout", out)
    err = io.StringIO()
    monkeypatch.setattr("agent_client.mcp_bridge.sys.stderr", err)
    run_stdio("tok", "http://127.0.0.1:8765")
    reply = json.loads(out.getvalue().splitlines()[0])
    names = [t["name"] for t in reply["result"]["tools"]]
    assert names == TOOL_NAMES


def test_tool_call_hub_down_is_unreachable_json(monkeypatch):
    def boom(_base: str, _token: str, _name: str, _arguments: dict) -> tuple[int, dict]:
        raise httpx.ConnectError("down")

    monkeypatch.setattr("agent_client.mcp_bridge.call_hub", boom)
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_context_contract",
                "arguments": {"purpose": "continue planning the trip"},
            },
        },
        "http://127.0.0.1:8765",
        "tok",
    )
    result = reply["result"]
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert payload["code"] == "hub_unreachable"
    assert payload["base"] == "http://127.0.0.1:8765"
    assert "Hub unreachable" in payload["message"]


def test_explain_resource_uses_the_explain_door(monkeypatch):
    def fake_call(base, token, name, arguments):
        assert name == "explain_subject"
        assert arguments == {"subject": "city"}
        return 200, {"status": "live", "value": "Lisbon"}

    monkeypatch.setattr("agent_client.mcp_bridge.call_hub", fake_call)
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "personal-context://explain?subject=city"},
        },
        "http://x",
        "tok",
    )
    payload = json.loads(reply["result"]["contents"][0]["text"])
    assert payload["value"] == "Lisbon"


def test_vault_resource_is_refused(monkeypatch):
    def fail_call(*_args, **_kwargs):
        raise AssertionError("vault read called the hub")

    monkeypatch.setattr("agent_client.mcp_bridge.call_hub", fail_call)
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": "personal-context://vault"},
        },
        "http://x",
        "tok",
    )
    text = reply["result"]["contents"][0]["text"]
    assert "not available" in text.lower()


def test_unreachable_mapping_is_json_code():
    down = map_tool_result(0, {"detail": "Connection refused"})
    payload = json.loads(down["content"][0]["text"])
    assert down["isError"] is True
    assert payload["code"] == "hub_unreachable"
    assert "Hub unreachable" in payload["message"]
