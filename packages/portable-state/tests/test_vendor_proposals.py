from pathlib import Path

from pch_archive.vendor.enqueue import enqueue_vendor_import

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"

CASES = (
    ("chatgpt", 3, "Prefers trains over planes"),
    ("claude", 2, "Vegetarian except fish"),
    ("gemini", 2, "Allergic to peanuts"),
    ("pam", 2, "Reads paper books"),
    ("ump", 2, "Uses a standing desk"),
)


def _origin_labels(mem: dict) -> list[str]:
    return [lab for lab in (mem.get("labels") or []) if str(lab).startswith("origin:")]


def test_structured_objects_enqueue_as_pending(hub):
    for name, count, sample in CASES:
        batch = enqueue_vendor_import(hub, FIXTURES / name)
        assert batch["enqueued"] == count
        memories = hub.list("memory")
        assert memories == []
        pending = [p for p in hub.list("proposal") if p.get("status") == "pending"]
        statements = [p["proposed_memory"]["statement"] for p in pending]
        assert sample in statements
        assert all(p["proposed_memory"]["authority"] == "proposed" for p in pending)
        assert all(p["submitted_by"].startswith("importer.") for p in pending)


def test_accept_preserves_origin_and_is_searchable(hub):
    batch = enqueue_vendor_import(hub, FIXTURES / "claude")
    pid = batch["proposal_ids"][0]
    prop = hub.get(pid)
    origin = _origin_labels(prop["proposed_memory"])
    assert origin
    stored = hub.decide_proposal(pid, True)
    assert stored["type"] == "memory"
    assert _origin_labels(stored) == origin
    found = hub.search(stored["statement"])
    ids = [row["id"] for row in found["results"] if row.get("type") == "memory"]
    assert stored["id"] in ids
