from pch_core.timeutil import now_iso


def test_concurrent_proposals_stay_non_canonical(hub):
    confirmed = hub.create(
        "memory",
        {"statement": "user likes tea", "kind": "semantic", "subject_ref": "pref.drink"},
    )
    link = hub.mint_link()
    paired = hub.pair(link["code"])
    actor = paired["connection_id"]
    hub.create_grant(actor, "read_active_projects", None, None)
    now = now_iso()
    mem = {
        "id": "mem_x",
        "type": "memory",
        "kind": "semantic",
        "statement": "user likes coffee",
        "subject_ref": "pref.drink",
        "owner": hub.person_id(),
        "space_id": "personal",
        "created_at": now,
        "updated_at": now,
        "labels": [],
        "classification": "personal",
        "source_refs": ["art_1"],
        "confidence": 0.4,
        "authority": "proposed",
        "retention": {"mode": "until_revoked"},
        "policy_tags": [],
        "version": 1,
        "sensitivity_flags": [],
    }
    p1 = hub.propose_memory(mem, actor, ["art_1"])
    p2 = hub.propose_memory({**mem, "id": "mem_y"}, actor, ["art_1"])
    assert p1["status"] in ("pending", "superseded")
    assert p2["status"] in ("pending", "superseded")
    still = hub.get(confirmed["id"])
    assert still["statement"] == "user likes tea"
