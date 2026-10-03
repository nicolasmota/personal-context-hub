from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from pch_core.errors import PolicyDenied
from pch_core.service import Hub

from pch_server.mcp.resources import audit_resource, brief_resource, profile_resource, self_resource
from pch_server.mcp.tools_context import attach_tools


class ToolHub:
    """Minimal MCP-like dispatcher used by REST `/v1/mcp/tools/{name}` and tests."""

    def __init__(self, hub: Hub) -> None:
        self.hub = hub
        self._current_actor = "owner"
        self._tools: dict[str, Any] = {}
        attach_tools(self, hub)

    def tool(self):
        def deco(fn):
            self._tools[fn.__name__] = fn
            return fn

        return deco

    def call(self, name: str, actor: str, **kwargs):
        self._current_actor = actor
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name](**kwargs)

    def resource(self, uri: str, actor: str) -> Any:
        parsed = urlparse(uri)
        if parsed.scheme == "pch" and parsed.netloc == "vault":
            raise PolicyDenied("the whole personal record is not available")
        if parsed.scheme == "pch" and parsed.netloc == "explain":
            self._current_actor = actor
            subject = (parse_qs(parsed.query).get("subject") or [""])[0]
            return self.call("explain_subject", actor, subject=subject)
        if parsed.scheme == "pch" and parsed.netloc == "impact":
            evidence_id = (parse_qs(parsed.query).get("evidence") or [""])[0]
            return self.call("source_impact", actor, evidence_id=evidence_id)
        if parsed.scheme == "pch" and parsed.netloc == "proposal-status":
            return self.call("proposal_status", actor)
        if uri.endswith("/profile") or "/profile" in uri:
            return profile_resource(self.hub, actor)
        if uri.endswith("/brief") or "/brief" in uri:
            pid = uri.split("/projects/")[-1].split("/")[0]
            return brief_resource(self.hub, pid, actor)
        if uri.endswith("connection/self") or uri.endswith("/self"):
            return self_resource(self.hub, actor)
        if "audit" in uri:
            return audit_resource(self.hub, actor)
        raise KeyError(uri)
