"""User SDK vs lab package (019). Fails while eval/loop live on agent-client."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONSTITUTION = ROOT / ".specify" / "memory" / "constitution.md"


def test_sdk_help_is_user_surface() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agent_client", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout.lower()
    assert "mcp-bridge" in out
    assert "plugin" not in out
    assert "vault-init" in out
    assert "compile" in out
    assert "demo-agent" in out
    assert "eval" not in out
    assert "loop" not in out
    assert " sim" not in out and "\nsim" not in out


def test_importing_sdk_main_does_not_load_lab() -> None:
    code = (
        "import sys, agent_client.__main__ as m; "
        "names = set(sys.modules); "
        "assert 'eval_harness' not in names, sorted(n for n in names if 'eval_harness' in n or 'devloop' in n); "
        "assert 'agent_client.devloop' not in names; "
        "assert 'agent_client.eval' not in names; "
        "assert 'agent_client.sim' not in names"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_lab_package_and_script() -> None:
    path = ROOT / "packages" / "eval-harness" / "pyproject.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert data["project"]["name"] == "eval-harness"
    assert data["project"]["scripts"]["pch-lab"]
    import eval_harness.devloop.cli as lab_cli

    assert callable(lab_cli.dispatch_loop)


def test_lab_loop_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "eval_harness", "loop", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "start" in result.stdout.lower()


def test_docs_and_constitution_name_lab() -> None:
    if CONSTITUTION.is_file():
        constitution = CONSTITUTION.read_text(encoding="utf-8")
        assert "`packages/eval-harness`" in constitution
        assert "**Version**: 2.0.0" in constitution
        sdk_bullet = [line for line in constitution.splitlines() if "`packages/agent-client`" in line]
        assert sdk_bullet
        assert "evaluation harness" not in " ".join(sdk_bullet).lower()
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "pch-lab loop" in agents
    assert "uv run pch-sdk loop" not in agents
    develop = (ROOT / "docs" / "develop.md").read_text(encoding="utf-8")
    assert "pch-lab loop" in develop
    cli = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    assert "pch-lab loop" in cli
    assert "uv run pch-sdk eval" not in cli
    assert "does not run loop" in cli


def test_server_package_does_not_depend_on_lab() -> None:
    data = tomllib.loads((ROOT / "packages" / "loopback-service" / "pyproject.toml").read_text(encoding="utf-8"))
    deps = " ".join(data["project"]["dependencies"])
    assert "eval-harness" not in deps
    assert "eval_harness" not in deps


def test_importing_server_app_does_not_load_lab() -> None:
    code = (
        "import sys; "
        "from loopback_service.rest.app import create_app; "
        "from pathlib import Path; "
        "from trust_kernel.service import Hub; "
        "from tempfile import TemporaryDirectory; "
        "td = TemporaryDirectory(); "
        "hub = Hub(Path(td.name), plain=True); "
        "create_app(hub, sim_enabled=False, catalog_refresh=False); "
        "names = set(sys.modules); "
        "assert 'eval_harness' not in names, sorted(n for n in names if n.startswith('eval_harness')); "
        "hub.close(); td.cleanup()"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_sdk_lab_verbs_do_not_load_lab() -> None:
    help_run = subprocess.run(
        [sys.executable, "-m", "agent_client", "loop", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_run.returncode == 2
    assert "pch-lab" in help_run.stderr
    code = """
import sys
from agent_client.__main__ import main
try:
    main(['eval', 'run'])
except SystemExit as exc:
    assert exc.code == 2
else:
    raise AssertionError('expected SystemExit')
assert 'eval_harness' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
