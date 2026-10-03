import json
import zipfile
from pathlib import Path

from trust_kernel.ingest.vendor_memory import import_vendor_file


def test_chatgpt_import_is_untrusted_and_does_not_grant(hub, tmp_path: Path):
    before = hub.list("grant")
    src = tmp_path / "memory.json"
    src.write_text(
        json.dumps(
            [
                {"id": "m1", "content": "Prefers trains to flights", "enabled": True},
                {"id": "m2", "content": "Disabled fact", "enabled": False},
            ]
        ),
        encoding="utf-8",
    )
    result = import_vendor_file(hub, src)
    assert result["imported"] == 1
    assert result["provider"] == "chatgpt"
    row = hub.get(result["ids"][0])
    assert row["authority"] == "source_imported"
    assert row["untrusted"] is True
    assert "origin:chatgpt" in row["labels"]
    assert hub.list("grant") == before
    again = import_vendor_file(hub, src)
    assert again["imported"] == 0
    assert again["skipped"] == 1


def test_claude_memory_files_and_zip_without_transcripts(hub, tmp_path: Path):
    payload = {
        "conversations_memory": "Lives in Lisbon.",
        "memory_files": [{"path": "/preferences.md", "content": "Prefers morning meetings."}],
        "project_memories": {"proj-1": "Shipping the atlas plan."},
    }
    src = tmp_path / "memories.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    result = import_vendor_file(hub, src)
    statements = {hub.get(item_id)["statement"] for item_id in result["ids"]}
    assert statements == {
        "Lives in Lisbon.",
        "Prefers morning meetings.",
        "Shipping the atlas plan.",
    }
    chats = tmp_path / "chats.zip"
    with zipfile.ZipFile(chats, "w") as archive:
        archive.writestr("conversations.json", "[]")
    try:
        import_vendor_file(hub, chats)
    except ValueError as exc:
        assert "chat transcripts" in str(exc)
    else:
        raise AssertionError("conversations.zip should not import")
