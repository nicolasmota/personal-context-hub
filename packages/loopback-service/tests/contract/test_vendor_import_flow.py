from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[3] / "pch-archive" / "tests" / "fixtures" / "vendor"


def test_vendor_import_enqueues_then_accept_searchable(client):
    r = client.post("/v1/import/vendor", json={"path": str(FIXTURES / "claude")})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "claude"
    assert body["enqueued"] == 2
    pending = client.get("/v1/memories/proposals?status=pending").json()
    assert len(pending) >= 2
    statement = pending[0]["proposed_memory"]["statement"]
    search = client.get("/v1/search", params={"q": statement, "type": "memory"}).json()
    assert search["results"] == []
    acc = client.post(f"/v1/memories/proposals/{pending[0]['id']}/accept", json={})
    assert acc.status_code == 200
    found = client.get("/v1/search", params={"q": statement, "type": "memory"}).json()
    assert found["results"]


def test_unknown_layout_is_400(client):
    r = client.post("/v1/import/vendor", json={"path": str(FIXTURES / "unknown")})
    assert r.status_code == 400
    assert client.get("/v1/memories/proposals?status=pending").json() == []


def test_vendor_zip_rejected_by_pca_stage(client, tmp_path: Path):
    bogus = tmp_path / "not.pca"
    bogus.write_bytes(b"not-a-pca")
    r = client.post("/v1/import/stage", json={"path": str(bogus), "passphrase": "x"})
    assert r.status_code == 400
