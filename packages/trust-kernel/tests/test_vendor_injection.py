from pathlib import Path

import pytest
from pch_archive.vendor.enqueue import decide_archive, enqueue_vendor_import

FIXTURES = Path(__file__).resolve().parent.parent.parent / "pch-archive" / "tests" / "fixtures" / "vendor"


@pytest.mark.forbidden_context
def test_vendor_injection_does_not_change_grants(hub):
    grants_before = hub.list("grant")
    batch = enqueue_vendor_import(hub, FIXTURES / "chatgpt")
    decide_archive(hub, batch["id"], admit=True)
    grants_after = hub.list("grant")
    assert grants_after == grants_before
    pending = [p for p in hub.list("proposal") if p.get("status") == "pending"]
    assert pending
    assert all(p.get("status") != "auto_accepted" for p in hub.list("proposal"))
    actions = [a for a in hub.list("action_intent")]
    assert actions == []
