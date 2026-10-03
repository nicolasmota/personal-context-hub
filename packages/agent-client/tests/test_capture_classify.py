from pch_sdk.capture_guidance import follow_capture_guidance
from pch_sdk.mcp_bridge import handle_message


def _tools():
    reply = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "http://x", "tok")
    return reply["result"]["tools"]


def test_follow_capture_guidance_classifies_paraphrased_turns():
    lines = [
        "Can you help me with the trip?",
        "Remember we are two travelers and dropped London.",
        "Keep the budget tight.",
    ]
    assert follow_capture_guidance(lines, _tools()) == [
        "get_context_contract",
        "propose_memory",
        "propose_memory",
    ]


def test_follow_capture_guidance_still_requires_tool_descriptions():
    tools = [
        {"name": "get_context_contract", "description": "get context contract"},
        {"name": "propose_memory", "description": "propose memory"},
    ]
    try:
        follow_capture_guidance(["Can you help me with the trip?"], tools)
    except ValueError as exc:
        assert "task-start" in str(exc) or "durable" in str(exc)
    else:
        raise AssertionError("expected missing-guidance error")
