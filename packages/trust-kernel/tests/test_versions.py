from pch_core.errors import VersionConflict


def test_if_match(hub):
    mem = hub.create("memory", {"statement": "v1", "kind": "semantic"})
    updated = hub.patch(mem["id"], {"statement": "v2"}, if_match=mem["version"])
    assert updated["version"] == mem["version"] + 1
    try:
        hub.patch(mem["id"], {"statement": "v3"}, if_match=mem["version"])
        raise AssertionError("expected conflict")
    except VersionConflict:
        pass
    hist = hub.versions(mem["id"])
    assert len(hist) >= 2
