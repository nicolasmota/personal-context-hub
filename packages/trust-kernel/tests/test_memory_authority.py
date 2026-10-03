def test_user_edit_not_reverted(hub):
    mem = hub.create("memory", {"statement": "mornings", "kind": "semantic", "subject_ref": "pref.meetings"})
    hub.patch(mem["id"], {"statement": "afternoons"}, if_match=mem["version"])
    got = hub.get(mem["id"])
    assert got["statement"] == "afternoons"
    assert got["authority"] == "user_confirmed"
