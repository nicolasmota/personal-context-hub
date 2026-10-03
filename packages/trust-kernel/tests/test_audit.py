

def test_hash_chain(hub):
    hub.create("memory", {"statement": "hello", "kind": "semantic"})
    result = hub.verify_events()
    assert result["ok"] is True
    assert result["count"] >= 1
