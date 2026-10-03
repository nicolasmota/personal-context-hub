"""Second real runtime: Hermes MCP (020). Fails while only Cursor is validated."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from pch_core.service import Hub
from pch_server.pairing.catalog import list_assistants
from pch_server.rest.app import create_app

ROOT = Path(__file__).resolve().parents[3]
PAIR_DOC = ROOT / "docs" / "guides" / "pair-an-agent.md"
EVAL_HARNESS = ROOT / "packages" / "pch-lab" / "src" / "pch_lab" / "eval" / "harness.py"


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


def test_catalog_validates_hermes_not_openclaw() -> None:
    by_id = {row["id"]: row for row in list_assistants()}
    assert by_id["cursor"]["validated"] is True
    assert by_id["hermes"]["validated"] is True
    assert by_id["openclaw"]["validated"] is False


def test_docs_name_hermes_validated_not_recipe_only() -> None:
    pair = PAIR_DOC.read_text(encoding="utf-8")
    assert "| `hermes` | Hermes | Recipe |" not in pair
    assert "| `hermes` | Hermes | Validated |" in pair
    started = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")
    assert "Cursor and Hermes" in started
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Hermes" in readme and "validated" in readme.lower()
    assert "Cursor IDE is not launched" in pair


def test_eval_pairing_does_not_wear_catalog_runtime_ids() -> None:
    text = EVAL_HARNESS.read_text(encoding="utf-8")
    assert '_pair(hub, "hermes"' not in text
    assert '_pair(hub, "openclaw"' not in text


def test_catalog_cursor_notes_name_recipe_stdio_not_ide() -> None:
    by_id = {row["id"]: row for row in list_assistants()}
    notes = by_id["cursor"]["notes"].lower()
    assert "stdio" in notes
    assert "mcpservers" in notes.replace("_", "").replace("-", "")
    assert "not launched" in notes or "ide is not" in notes


def _wait_healthy(base: str) -> None:
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/health", timeout=0.3).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.05)
    raise AssertionError(f"hub not healthy at {base}")


def _bridge_from_recipe(recipe: dict) -> dict:
    snippet = recipe["snippet"]
    if "mcpServers" in snippet:
        return snippet["mcpServers"]["personal-context-hub"]
    if "mcp_servers" in snippet:
        return snippet["mcp_servers"]["personal-context-hub"]
    raise AssertionError(sorted(snippet))


def _stdio_get_context_contract(tmp_path: Path, assistant: str, client_name: str) -> None:
    hub = Hub(tmp_path / "hub", plain=True)
    hub.setup("Tester")
    trip = hub.create("project", {"title": "Europe Trip", "status": "active"})
    app = create_app(hub, sim_enabled=False, catalog_refresh=False)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    _wait_healthy(base)
    headers = {"Authorization": f"Bearer {hub.owner_token}"}
    try:
        link = httpx.post(
            f"{base}/v1/connections/links", headers=headers, json={"name": assistant}
        ).json()
        httpx.post(f"{base}/v1/connections/pair", json={"code": link["code"]}, timeout=10)
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
            json={"assistant": assistant},
            timeout=10,
        )
        assert recipe.status_code == 200, recipe.text
        bridge = _bridge_from_recipe(recipe.json())
        env = {**os.environ, **bridge["env"]}
        proc = subprocess.Popen(
            [bridge["command"], *bridge["args"]],
            cwd=str(tmp_path),
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
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": client_name},
                    },
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
                        "name": "get_context_contract",
                        "arguments": {"purpose": "continue planning the trip"},
                    },
                },
            )
            assert "result" in called
            blob = json.dumps(called)
            assert "Hub unreachable" not in blob
            assert trip["id"] in blob or "Europe Trip" in blob
        finally:
            proc.kill()
            proc.wait(timeout=5)
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        hub.close()


def test_cursor_recipe_stdio_get_context_contract(tmp_path: Path) -> None:
    _stdio_get_context_contract(tmp_path, "cursor", "cursor-proof")


def test_hermes_recipe_stdio_get_context_contract(tmp_path: Path) -> None:
    _stdio_get_context_contract(tmp_path, "hermes", "hermes-proof")


@pytest.mark.skipif(shutil.which("hermes") is None, reason="hermes CLI not on PATH")
def test_hermes_cli_mcp_test_isolated_home(tmp_path: Path) -> None:
    person_config = Path.home() / ".hermes" / "config.yaml"
    before = person_config.stat().st_mtime if person_config.is_file() else None
    hub = Hub(tmp_path / "hub", plain=True)
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
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    try:
        link = httpx.post(f"{base}/v1/connections/links", headers=headers, json={"name": "hermes"}).json()
        httpx.post(f"{base}/v1/connections/pair", json={"code": link["code"]}, timeout=10)
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
            json={"assistant": "hermes"},
            timeout=10,
        )
        bridge = recipe.json()["snippet"]["mcp_servers"]["personal-context-hub"]
        env = {**os.environ, "HERMES_HOME": str(hermes_home)}
        add = subprocess.run(
            [
                "hermes",
                "mcp",
                "add",
                "personal-context-hub",
                "--command",
                bridge["command"],
                "--env",
                f"PCH_TOKEN={bridge['env']['PCH_TOKEN']}",
                f"PCH_BASE={bridge['env']['PCH_BASE']}",
                "--args",
                *bridge["args"],
            ],
            cwd=str(tmp_path),
            env=env,
            input="Y\n",
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert add.returncode == 0, add.stdout + add.stderr
        saved = (hermes_home / "config.yaml").read_text(encoding="utf-8")
        assert "personal-context-hub" in saved
        assert bridge["env"]["PCH_TOKEN"] in saved
        probed = subprocess.run(
            ["hermes", "mcp", "test", "personal-context-hub"],
            cwd=str(tmp_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert probed.returncode == 0, probed.stdout + probed.stderr
        combined = (probed.stdout + probed.stderr).lower()
        assert "get_context_contract" in combined or "tool" in combined
        assert "fail" not in combined or "connected" in combined
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        hub.close()
    after = person_config.stat().st_mtime if person_config.is_file() else None
    assert after == before
