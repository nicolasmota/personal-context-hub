from pch_core.service import OWNER


class _OnlyAlpha:
    def relevance(self, text: str, purpose: str) -> float:
        return 1.0 if "alpha" in text.lower() else 0.0


def test_injected_retriever_picks_the_project(hub):
    hub.retriever = _OnlyAlpha()
    alpha = hub.create("project", {"title": "Alpha", "status": "active", "charter": ""})
    hub.create("project", {"title": "Beta", "status": "active", "charter": ""})
    contract = hub.get_context_contract(OWNER, "something else entirely")
    assert contract["situation"]["project_id"] == alpha["id"]
