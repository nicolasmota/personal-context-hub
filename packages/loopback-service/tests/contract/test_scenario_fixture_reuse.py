from pathlib import Path

from trust_kernel.testing.scenarios import load_scenarios


def test_server_loads_scenarios_from_core():
    ids = {row["id"] for row in load_scenarios()}
    assert "privacy" in ids
    assert "changing_preferences" in ids
    root = Path(__file__).resolve().parents[4]
    text = (root / "packages/loopback-service/pyproject.toml").read_text(encoding="utf-8")
    assert "eval-harness" not in text
