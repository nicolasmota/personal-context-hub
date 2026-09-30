from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_removed_surfaces_are_absent() -> None:
    for relative in ("plugins", "frontend", "apps/hub-desktop", "experimental"):
        assert not (ROOT / relative).exists(), relative
