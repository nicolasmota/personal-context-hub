import threading
from pathlib import Path

from pch_core.service import Hub


def test_vault_persists(tmp_path: Path):
    d = tmp_path / "v"
    h = Hub(d, plain=True)
    h.setup("A")
    p = h.create("project", {"title": "Atlas", "charter": "ship", "status": "active"})
    h.close()
    h2 = Hub(d, plain=True)
    got = h2.get(p["id"])
    assert got["title"] == "Atlas"
    h2.close()


def test_sqlcipher_row_factory(tmp_path: Path):
    h = Hub(tmp_path / "cipher", plain=False)
    h.setup("Nick")
    assert h.setup_status()["initialized"] is True
    assert h.owner_token
    h.close()


def test_concurrent_lists_do_not_raise(hub: Hub):
    hub.create("project", {"title": "Europe Trip", "charter": "trip", "status": "active"})
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(40):
                hub.list("project")
                hub.list("relation_proposal")
                hub.list("proposal")
        except BaseException as err:
            errors.append(err)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
