from pathlib import Path

from pch_archive.vendor.enqueue import enqueue_vendor_import

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"


def test_reimport_skips_pending_and_accepted(hub):
    first = enqueue_vendor_import(hub, FIXTURES / "claude")
    assert first["enqueued"] == 2
    hub.decide_proposal(first["proposal_ids"][0], True)
    hub.decide_proposal(first["proposal_ids"][1], False)
    second = enqueue_vendor_import(hub, FIXTURES / "claude")
    assert second["enqueued"] == 0
    assert second["skipped"] >= 2
    memories = hub.list("memory")
    assert len(memories) == 1
