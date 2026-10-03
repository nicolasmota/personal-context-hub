from trust_kernel.ids import new_id
from trust_kernel.schema.portability import VendorImportBatch
from trust_kernel.timeutil import now_iso


def test_vendor_import_batch_round_trip():
    created = now_iso()
    batch = VendorImportBatch(
        id=new_id("vendor_import_batch"),
        source="claude",
        path_basename="claude.zip",
        status="enqueued",
        archive_status="pending",
        memory_item_count=2,
        conversation_count=1,
        proposal_ids=["prop_1"],
        skipped_fingerprints=[],
        items=[],
        created_at=created,
        owner="per_test",
    )
    dumped = batch.model_dump(mode="json")
    again = VendorImportBatch.model_validate(dumped)
    assert again.source == "claude"
    assert again.archive_status == "pending"
    assert again.id.startswith("vib_")
