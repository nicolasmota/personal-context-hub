from agent_client.mcp_bridge import REMOVED_TOOLS


def test_removed_agent_tools_are_not_callable(client):
    for name in sorted(REMOVED_TOOLS):
        response = client.post(f"/v1/mcp/tools/{name}", json={})
        assert response.status_code == 404, name
