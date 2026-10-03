def test_export_import(client, tmp_path):
    client.post("/v1/projects", json={"title": "Atlas", "status": "active"})
    exported = client.post("/v1/export", json={"passphrase": "secret", "filters": {}}).json()
    assert exported["path"]
    staged = client.post("/v1/import/stage", json={"path": exported["path"], "passphrase": "secret"})
    assert staged.status_code == 200
    apply = client.post(f"/v1/import/staging/{staged.json()['id']}/apply", json={"resolutions": []})
    assert apply.status_code == 200
