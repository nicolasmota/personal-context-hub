from pathlib import Path

from pch_archive.vendor.enqueue import decide_archive, enqueue_vendor_import

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"


def test_discard_writes_no_artifacts(hub):
    batch = enqueue_vendor_import(hub, FIXTURES / "claude")
    assert batch["archive_status"] == "pending"
    decide_archive(hub, batch["id"], admit=False)
    assert hub.list("artifact") == []
    pending = [p for p in hub.list("proposal") if p.get("status") == "pending"]
    assert len(pending) == 2
    updated = hub.get(batch["id"])
    assert updated["archive_status"] == "discarded"


def test_admit_writes_untrusted_conversations(hub):
    batch = enqueue_vendor_import(hub, FIXTURES / "claude")
    decide_archive(hub, batch["id"], admit=True)
    arts = hub.list("artifact")
    assert arts
    assert all(a.get("untrusted") is True for a in arts)
    assert all(a.get("kind") == "conversation" for a in arts)
    assert all(a.get("authority") == "source_imported" for a in arts)
