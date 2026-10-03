"""Shared fake repo for devloop tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROADMAP = """# Roadmap
### E1 — Context Engine
**Spec:** `specs/004-context-engine/`
### E2 — Validade Temporal
**Spec:** `specs/005-temporal-validity/`
### E3 — Estado de Projeto
**Spec:** —
"""


def make_repo(root: Path) -> Path:
    (root / "docs").mkdir()
    (root / "docs" / "VISION.md").write_text("thesis\n", encoding="utf-8")
    (root / "docs" / "ROADMAP.md").write_text(ROADMAP, encoding="utf-8")
    (root / ".specify").mkdir()
    for name in (
        "001-personal-context-hub",
        "004-context-engine",
        "005-temporal-validity",
        "009-fixture",
    ):
        d = root / "specs" / name
        d.mkdir(parents=True)
        (d / "spec.md").write_text(f"# {name}\n", encoding="utf-8")
    (root / ".specify" / "feature.json").write_text(
        '{"feature_directory":"specs/009-fixture"}\n', encoding="utf-8"
    )
    return root


@pytest.fixture
def loop_repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path)
