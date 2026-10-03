from pathlib import Path

from pch_archive.vendor.detect import detect_source

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "vendor"


def test_detect_chatgpt():
    assert detect_source(FIXTURES / "chatgpt") == "chatgpt"


def test_detect_claude():
    assert detect_source(FIXTURES / "claude") == "claude"


def test_detect_gemini():
    assert detect_source(FIXTURES / "gemini") == "gemini"


def test_detect_pam():
    assert detect_source(FIXTURES / "pam") == "pam"


def test_detect_ump():
    assert detect_source(FIXTURES / "ump") == "ump"


def test_detect_unknown():
    assert detect_source(FIXTURES / "unknown") == "unknown"


def test_pam_wins_over_vendor(tmp_path: Path):
    dest = tmp_path / "mix"
    dest.mkdir()
    (dest / "conversations.json").write_text("[]", encoding="utf-8")
    (dest / "memory-store.json").write_text(
        '{"schema": "portable-ai-memory", "schema_version": "1.0", "memories": []}',
        encoding="utf-8",
    )
    assert detect_source(dest) == "pam"
