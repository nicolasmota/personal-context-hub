"""SC-002: secrets hygiene checker (red before green)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "check_secrets.py"


def _run_checker(cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exists() -> None:
    assert SCRIPT.is_file()


def test_clean_repo_passes() -> None:
    result = _run_checker()
    assert result.returncode == 0, result.stdout + result.stderr


def test_tracked_env_fails(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", ".env"], cwd=repo, check=True, capture_output=True)
    # Run checker against this temp repo by copying script logic via env
    env = os.environ.copy()
    env["PCH_SECRETS_REPO"] = str(repo)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 1
    assert ".env" in result.stdout or ".env" in result.stderr


def test_tracked_pch_dir_fails(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    pch = repo / ".pch"
    pch.mkdir()
    (pch / "vault.db").write_bytes(b"x")
    subprocess.run(["git", "add", "-f", ".pch/vault.db"], cwd=repo, check=True, capture_output=True)
    env = os.environ.copy()
    env["PCH_SECRETS_REPO"] = str(repo)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 1
    assert ".pch" in (result.stdout + result.stderr)


def test_deny_patterns_documented_in_script() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for token in (".env", "google_oauth.json", ".cursor/mcp.json", ".pch", ".pch-sim", ".vault"):
        assert token in text
