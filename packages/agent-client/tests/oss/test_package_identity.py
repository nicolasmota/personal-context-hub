"""Hub-family package identity (015). Fails until pcl-* / pca are gone."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CONSTITUTION = ROOT / ".specify" / "memory" / "constitution.md"

HUB_PACKAGES = [
    (ROOT / "packages" / "pch-core" / "pyproject.toml", "pch-core"),
    (ROOT / "packages" / "pch-server" / "pyproject.toml", "pch-server"),
    (ROOT / "packages" / "pch-sdk" / "pyproject.toml", "pch-sdk"),
    (ROOT / "packages" / "pch-lab" / "pyproject.toml", "pch-lab"),
    (ROOT / "packages" / "pch-archive" / "pyproject.toml", "pch-archive"),
]

FORBIDDEN_NAMES = frozenset({"pcl-core", "pcl-server", "pcl-sdk", "pcl-pca"})
FORBIDDEN_DIRS = (
    ROOT / "packages" / "pcl-core" / "src" / "pcl_core",
    ROOT / "packages" / "pcl-server" / "src" / "pcl_server",
    ROOT / "packages" / "pcl-sdk" / "src" / "pcl_sdk",
    ROOT / "packages" / "pca" / "src" / "pca",
    ROOT / "packages" / "pch-core" / "src" / "pcl_core",
    ROOT / "packages" / "pch-server" / "src" / "pcl_server",
    ROOT / "packages" / "pch-sdk" / "src" / "pcl_sdk",
    ROOT / "packages" / "pch-archive" / "src" / "pca",
)
LIVE_IMPORT_DIRS = (
    ROOT / "packages" / "pch-core" / "src" / "pch_core",
    ROOT / "packages" / "pch-server" / "src" / "pch_server",
    ROOT / "packages" / "pch-sdk" / "src" / "pch_sdk",
    ROOT / "packages" / "pch-lab" / "src" / "pch_lab",
    ROOT / "packages" / "pch-archive" / "src" / "pch_archive",
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
    sdk = _scripts(ROOT / "packages" / "pch-sdk" / "pyproject.toml")
    lab = _scripts(ROOT / "packages" / "pch-lab" / "pyproject.toml")
    server = _scripts(ROOT / "packages" / "pch-server" / "pyproject.toml")
    archive = _scripts(ROOT / "packages" / "pch-archive" / "pyproject.toml")
    assert "pch-sdk" in sdk
    assert "pch-lab" in lab
    assert "pch-server" in server
    assert "pch-archive" in archive
    assert "pcl-sdk" not in sdk
    assert "pcl-server" not in server
    assert "pca" not in archive


def test_recipe_uses_pch_sdk() -> None:
    catalog = (
        ROOT / "packages" / "pch-server" / "src" / "pch_server" / "pairing" / "catalog.py"
    )
    text = catalog.read_text(encoding="utf-8")
    assert "-m" in text and "pch_sdk" in text
    assert "pcl_sdk" not in text


def test_stranger_docs_use_hub_family() -> None:
    for path in STRANGER_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "pch-core" in text, path
        assert "packages/pcl-core" not in text or "formerly" in text.lower()


def test_constitution_package_boundaries() -> None:
    if not CONSTITUTION.is_file():
        pytest.skip("local Speckit constitution is not in this checkout")
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "`packages/pch-core`" in text
    assert "`packages/pcl-core`" not in text.split("Package boundaries:")[-1]


def test_archive_import_tests_remain() -> None:
    tests = ROOT / "packages" / "pch-archive" / "tests"
    assert (tests / "test_roundtrip.py").is_file()
    assert (tests / "test_format.py").is_file()
