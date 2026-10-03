def test_ask_answers_from_vault_memory(hub):
    mem = hub.create(
        "memory",
        {"statement": "Atlas prefers cited briefs", "kind": "semantic", "project_id": None},
    )
    out = hub.ask("O que o Atlas prefere?")
    assert "cited briefs" in out["answer"].lower()
    assert any(c["id"] == mem["id"] for c in out["citations"])


def test_ask_admits_when_vault_has_no_match(hub):
    hub.create(
        "memory",
        {"statement": "Atlas prefers cited briefs", "kind": "semantic", "project_id": None},
    )
    out = hub.ask("o que eu gosto de comer?")
    assert out["citations"] == []
    assert "não encontrei" in out["answer"].lower()
