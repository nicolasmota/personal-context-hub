"""Python 3.12 floor (017). Fails while 3.14 is still the minimum."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CONSTITUTION = ROOT / ".specify" / "memory" / "constitution.md"

PYPROJECTS = [
    ROOT / "pyproject.toml",
    ROOT / "packages" / "pch-core" / "pyproject.toml",
    ROOT / "packages" / "pch-server" / "pyproject.toml",
    ROOT / "packages" / "pch-sdk" / "pyproject.toml",
    ROOT / "packages" / "pch-archive" / "pyproject.toml",
    ROOT / "packages" / "pch-lab" / "pyproject.toml",
]

DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "getting-started.md",
    ROOT / "docs" / "develop.md",
    ROOT / "docs" / "reference" / "cli.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "AGENTS.md",
]


def test_requires_python_is_3_12_floor() -> None:
    for path in PYPROJECTS:
        text = path.read_text(encoding="utf-8")
        assert 'requires-python = ">=3.12"' in text, path
        assert 'requires-python = ">=3.14"' not in text, path


def test_lockfile_and_tools_follow_floor() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.12"' in lock
    assert 'requires-python = ">=3.14"' not in lock
    ruff = (ROOT / "ruff.toml").read_text(encoding="utf-8")
    assert 'target-version = "py312"' in ruff
    assert 'target-version = "py314"' not in ruff
    mypy = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'python_version = "3.12"' in mypy
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "Python 3.12+" in makefile
    assert "Python 3.14 workspace" not in makefile


def test_ci_uses_python_3_12() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "3.12" in ci
    assert "make lint" in ci
    assert "make test" in ci


def test_docs_do_not_require_3_14() -> None:
    for path in DOCS:
        text = path.read_text(encoding="utf-8")
        assert "3.12" in text, path
        lowered = text.lower()
        for needle in (
            "requires python 3.14",
            "python 3.14 is pulled",
            "python 3.14 via uv is the runtime",
            "- python 3.14\n",
        ):
            assert needle not in lowered, f"{path}: still requires 3.14 ({needle!r})"


def test_constitution_runtime_is_3_12_or_newer() -> None:
    if not CONSTITUTION.is_file():
        pytest.skip("local Speckit constitution is not in this checkout")
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "Python 3.12 or newer via `uv` is the runtime" in text
    assert "Python 3.14 via `uv` is the runtime" not in text
    assert "**Version**: 2.0.0" in text
