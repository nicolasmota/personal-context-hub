from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from pch_core.service import Hub
from pch_server.pairing.catalog import ASSISTANTS
from pch_server.rest.app import create_app


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _rpc(proc: subprocess.Popen, msg: dict) -> dict:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, proc.stderr.read() if proc.stderr else "no stdout"
    return json.loads(line)


def test_all_supported_assistants_connect_from_tmp(tmp_path: Path):
    data = tmp_path / "hub"
    hub = Hub(data, plain=True)
    hub.setup("Tester")
    app = create_app(hub, sim_enabled=False, catalog_refresh=False)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/health", timeout=0.3).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    headers = {"Authorization": f"Bearer {hub.owner_token}"}
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    try:
        for assistant in ASSISTANTS:
            aid = assistant["id"]
            link = httpx.post(f"{base}/v1/connections/links", headers=headers, json={"name": aid}).json()
            httpx.post(
                f"{base}/v1/connections/pair",
                json={"code": link["code"]},
                timeout=10,
            )
            httpx.post(
                f"{base}/v1/grants",
                headers=headers,
                json={
                    "connection_id": link["connection_id"],
                    "capabilities": ["memory.retrieve", "profile.read", "project.read"],
                    "classification_ceiling": "private",
                },
                timeout=10,
            )
            recipe = httpx.post(
                f"{base}/v1/connections/{link['connection_id']}/recipe",
                headers=headers,
                json={"assistant": aid},
                timeout=10,
            )
            assert recipe.status_code == 200, recipe.text
            snippet = recipe.json()["snippet"]
            if aid == "hermes":
                bridge = snippet["mcp_servers"]["personal-context-hub"]
            elif aid == "openclaw":
                bridge = snippet["mcp"]["servers"]["personal-context-hub"]
            else:
                bridge = snippet["mcpServers"]["personal-context-hub"]
            env = {**os.environ, **bridge["env"]}
            proc = subprocess.Popen(
                [bridge["command"], *bridge["args"]],
                cwd=str(cwd),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                init = _rpc(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t"}},
                    },
                )
                assert "result" in init
                called = _rpc(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "search_personal_context",
                            "arguments": {"query": "Atlas", "purpose": "test"},
                        },
                    },
                )
                blob = json.dumps(called)
                assert "Hub unreachable" not in blob
                assert "result" in called
            finally:
                proc.kill()
                proc.wait(timeout=5)
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_recipe_command_is_pinned_interpreter():
    from pch_server.pairing.catalog import _bridge

    bridge = _bridge("tok", "http://127.0.0.1:8765")
    assert Path(bridge["command"]).resolve() == Path(sys.executable).resolve()
    assert bridge["args"] == ["-m", "pch_sdk", "mcp-bridge"]
