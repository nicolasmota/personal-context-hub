from pathlib import Path

from pch_core.service import Hub


def test_setup_resume(tmp_path: Path):
    h = Hub(tmp_path, plain=True)
    assert h.setup_status()["initialized"] is False
    assert h.setup_status()["name"] is None
    h.setup("Nick")
    status = h.setup_status()
    assert status["initialized"] is True
    assert status["name"] == "Nick"
    spaces = h.list("space")
    profiles = h.list("profile")
    h.setup("Nicholas")
    assert h.setup_status()["name"] == "Nicholas"
    assert len(h.list("space")) == len(spaces) == 1
    assert len(h.list("profile")) == len(profiles) == 1
    h.close()
