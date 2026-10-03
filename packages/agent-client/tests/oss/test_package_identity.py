"""Hub-family package identity (015). Fails until pcl-* / pca are gone."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CONSTITUTION = ROOT / ".specify" / "memory" / "constitution.md"

HUB_PACKAGES = [
    (ROOT / "packages" / "trust-kernel" / "pyproject.toml", "trust-kernel"),
    (ROOT / "packages" / "loopback-service" / "pyproject.toml", "loopback-service"),
    (ROOT / "packages" / "agent-client" / "pyproject.toml", "agent-client"),
    (ROOT / "packages" / "eval-harness" / "pyproject.toml", "eval-harness"),
    (ROOT / "packages" / "portable-state" / "pyproject.toml", "portable-state"),
]

FORBIDDEN_NAMES = frozenset({"pcl-core", "pcl-server", "pcl-sdk", "pcl-pca"})
FORBIDDEN_DIRS = (
    ROOT / "packages" / "pcl-core" / "src" / "pcl_core",
    ROOT / "packages" / "pcl-server" / "src" / "pcl_server",
    ROOT / "packages" / "pcl-sdk" / "src" / "pcl_sdk",
    ROOT / "packages" / "pca" / "src" / "pca",
    ROOT / "packages" / "trust-kernel" / "src" / "pcl_core",
    ROOT / "packages" / "loopback-service" / "src" / "pcl_server",
    ROOT / "packages" / "agent-client" / "src" / "pcl_sdk",
    ROOT / "packages" / "portable-state" / "src" / "pca",
)
LIVE_IMPORT_DIRS = (
    ROOT / "packages" / "trust-kernel" / "src" / "trust_kernel",
    ROOT / "packages" / "loopback-service" / "src" / "loopback_service",
    ROOT / "packages" / "agent-client" / "src" / "agent_client",
    ROOT / "packages" / "eval-harness" / "src" / "eval_harness",
    ROOT / "packages" / "portable-state" / "src" / "portable_state",
)

STRANGER_DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "getting-started.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "AGENTS.md",
)


def _project_name(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return str(data["project"]["name"])


def _scripts(path: Path) -> dict[str, str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return dict((data.get("project") or {}).get("scripts") or {})


def test_hub_family_project_names() -> None:
    for path, expected in HUB_PACKAGES:
        assert path.is_file(), path
        name = _project_name(path)
        assert name == expected, (path, name)
        assert name not in FORBIDDEN_NAMES


def test_old_project_names_absent() -> None:
    leftovers = list((ROOT / "packages").glob("*/pyproject.toml"))
    for path in leftovers:
        if not path.is_file():
            continue
        name = _project_name(path)
        assert name not in FORBIDDEN_NAMES, path


def test_live_import_dirs() -> None:
    for path in LIVE_IMPORT_DIRS:
        assert path.is_dir(), path
    for path in FORBIDDEN_DIRS:
        assert not path.is_dir(), path


def test_console_scripts() -> None:
    sdk = _scripts(ROOT / "packages" / "agent-client" / "pyproject.toml")
    lab = _scripts(ROOT / "packages" / "eval-harness" / "pyproject.toml")
    server = _scripts(ROOT / "packages" / "loopback-service" / "pyproject.toml")
    archive = _scripts(ROOT / "packages" / "portable-state" / "pyproject.toml")
    assert "personal-context" in sdk
    assert "personal-context-lab" in lab
    assert "personal-context-server" in server
    assert "personal-context-archive" in archive
    assert "pcl-sdk" not in sdk
    assert "pcl-server" not in server
    assert "pca" not in archive


def test_recipe_uses_agent_client() -> None:
    catalog = (
        ROOT / "packages" / "loopback-service" / "src" / "loopback_service" / "pairing" / "catalog.py"
    )
    text = catalog.read_text(encoding="utf-8")
    assert "-m" in text and "agent_client" in text
    assert "pcl_sdk" not in text


def test_stranger_docs_use_hub_family() -> None:
    for path in STRANGER_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "trust-kernel" in text, path
        assert "packages/pcl-core" not in text or "formerly" in text.lower()


def test_constitution_package_boundaries() -> None:
    if not CONSTITUTION.is_file():
        pytest.skip("local Speckit constitution is not in this checkout")
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "`packages/trust-kernel`" in text
    assert "`packages/pcl-core`" not in text.split("Package boundaries:")[-1]


def test_archive_import_tests_remain() -> None:
    tests = ROOT / "packages" / "portable-state" / "tests"
    assert (tests / "test_roundtrip.py").is_file()
    assert (tests / "test_format.py").is_file()
