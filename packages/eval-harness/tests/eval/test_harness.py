from pathlib import Path

from pch_core.service import Hub
from pch_lab.eval.harness import run_eval


def test_killer_demo_accuracy():
    report = run_eval()
    assert report["metrics"]["retrieval_accuracy"] is True
    killer = next(c for c in report["cases"] if c["id"] == "killer_demo")
    assert killer["pass"] is True


def test_isolation_precision():
    report = run_eval()
    assert report["metrics"]["precision"] is True
    iso = next(c for c in report["cases"] if c["id"] == "isolation")
    assert iso["pass"] is True


def test_freshness_as_of():
    report = run_eval()
    assert report["metrics"]["freshness"] is True


def test_conflict_listed():
    report = run_eval()
    assert report["metrics"]["conflict_resolution"] is True


def test_correction_drop_london():
    report = run_eval()
    assert report["metrics"]["user_correction"] is True


def test_portability_and_revoke():
    report = run_eval()
    assert report["metrics"]["portability"] is True
    switch = next(c for c in report["cases"] if c["id"] == "runtime_switch")
    assert switch["pass"] is True


def test_assembly_cost_reported():
    report = run_eval()
    cost = report["metrics"]["assembly_cost_seconds"]
    assert isinstance(cost, float)
    assert 0 <= cost < 2.0
    assert report["all_pass"] is True
    assert {c["id"] for c in report["cases"]} == {
        "killer_demo",
        "temporal_conflict",
        "isolation",
        "runtime_switch",
    }


def test_eval_writes_tooling_labels(tmp_path: Path):
    run_eval(tmp_path)
    hub = Hub(tmp_path / "vault", plain=True)
    try:
        person = hub.get(hub.person_id())
        assert "eval" in (person.get("labels") or [])
        assert "test-tooling" in (person.get("labels") or [])
        guests = [c for c in hub.connections() if str(c.get("name", "")).startswith("guest-")]
        assert {c["name"] for c in guests} == {"guest-work", "guest-one", "guest-two"}
        for conn in guests:
            assert "eval" in (conn.get("labels") or [])
            assert "test-tooling" in (conn.get("labels") or [])
            assert (conn.get("runtime_info") or {}).get("harness") == "pch-lab-eval"
    finally:
        hub.close()
