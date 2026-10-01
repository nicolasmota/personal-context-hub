def test_declined_retry_does_not_execute(hub):
    link = hub.mint_link()
    paired = hub.pair(link["code"])
    actor = paired["connection_id"]
    a = hub.propose_action(actor, "send_message", "send hi", {}, [], "k1", contract_id="contract_retry")
    hub.decide_approval(a["id"], False)
    b = hub.propose_action(actor, "send_message", "send hi", {}, [], "k2", contract_id="contract_retry")
    assert b["status"] == "pending"
    assert b.get("declined_parent_id") == a["id"]
    try:
        hub.action_result(a["id"], "executed", actor)
        raise AssertionError("should not execute declined")
    except Exception:
        pass
