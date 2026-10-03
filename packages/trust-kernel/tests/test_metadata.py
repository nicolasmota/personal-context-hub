from trust_kernel.schema.metadata import Authority, Classification, UniversalMetadata
from trust_kernel.timeutil import now_iso


def test_metadata_enums():
    now = now_iso()
    m = UniversalMetadata(
        id="mem_1",
        type="memory",
        owner="per_1",
        created_at=now,
        updated_at=now,
        authority=Authority.USER_CONFIRMED,
        classification=Classification.PERSONAL,
    )
    assert m.version == 1
    assert m.confidence == 1.0
