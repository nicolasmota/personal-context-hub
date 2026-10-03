import json

import pytest
from trust_kernel.retrieval.candidate import candidate_from_row
from trust_kernel.retrieval.retriever import TokenOverlapRetriever
from trust_kernel.schema.contract import envelope_json_schema
from trust_kernel.service import OWNER


def _slim(contract: dict) -> dict:
    body = dict(contract)
    body.pop("contract_id", None)
    body.pop("assembled_at", None)
    return body


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


class _Noted(TokenOverlapRetriever):
    def find_candidates(self, rows, purpose, *, limit=None):
        found = super().find_candidates(rows, purpose, limit=limit)
        return [
            item.model_copy(update={"finder_notes": {"allowed": True, "canonical": True}})
            for item in found
        ]


class _Boom:
    def relevance(self, text: str, purpose: str) -> float:
        return 0.0

    def find_candidates(self, rows, purpose, *, limit=None):
        raise RuntimeError("finder down")


class _Dup(TokenOverlapRetriever):
    def find_candidates(self, rows, purpose, *, limit=None):
        match = next(row for row in rows if row.get("statement") == "alpha confirmed")
        return [
            candidate_from_row(match, purpose, 0.2),
            candidate_from_row(match, purpose, 0.9),
        ]


def test_agent_inferred_memory_is_not_a_live_item(hub):
    project = hub.create("project", {"title": "Alpha", "status": "active"})
    hub.create(
        "memory",
        {
            "statement": "alpha inferred",
            "kind": "semantic",
            "project_id": project["id"],
            "authority": "agent_inferred",
            "confidence": 0.2,
        },
    )
    hub.create(
        "memory",
        {
            "statement": "alpha confirmed",
            "kind": "semantic",
            "project_id": project["id"],
        },
    )
    contract = hub.get_context_contract(OWNER, "alpha", subject_ref=project["id"])
    statements = [item["body"].get("statement") for item in contract["memories"]]
    assert "alpha inferred" not in statements
    assert "alpha confirmed" in statements
    assert any(note["category"] == "policy_exclusion" for note in contract["omissions"])
    assert "finder_notes" not in json.dumps(contract)


def test_closed_conflict_without_a_project_keeps_only_the_live_value(hub):
    hub.create("preference", {"key": "city", "value": "Lisbon"})
    hub.supersede(hub.list("preference")[0]["id"], {"value": "Porto"})
    contract = hub.get_context_contract(OWNER, "where do I live")
    live = [
        item["body"]["value"]
        for item in contract["preferences"]
        if item["body"].get("key") == "city"
    ]
    assert live == ["Porto"]
    assert "Lisbon" not in json.dumps(contract["preferences"])
    excerpts = " ".join(
        candidate.get("excerpt") or "" for candidate in hub.last_compilation_trace["candidates"]
    )
    assert "porto" not in excerpts


def test_raising_finder_does_not_return_a_contract(hub):
    hub.create("project", {"title": "Alpha", "status": "active", "charter": "vault dump"})
    hub.retriever = _Boom()
    with pytest.raises(RuntimeError, match="finder down"):
        hub.get_context_contract(OWNER, "alpha")


def test_finder_notes_do_not_authorize_or_change_the_contract(hub):
    work = hub.create("project", {"title": "Work", "status": "active"})
    personal = hub.create("project", {"title": "Personal", "status": "active"})
    hub.create(
        "memory",
        {
            "statement": "alpha secret-offer",
            "kind": "semantic",
            "project_id": personal["id"],
        },
    )
    guest = _pair(hub, "work-guest")
    hub.create_grant(
        guest["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": work["id"]},
        "private",
    )
    hub.retriever = TokenOverlapRetriever()
    plain = hub.get_context_contract(guest["connection_id"], "alpha", subject_ref=work["id"])
    hub.retriever = _Noted()
    noted = hub.get_context_contract(guest["connection_id"], "alpha", subject_ref=work["id"])
    assert _slim(plain) == _slim(noted)
    assert "secret-offer" not in json.dumps(noted)
    assert all(
        candidate["finder_notes"].get("canonical") is True
        for candidate in hub.last_compilation_trace["candidates"]
    )


def test_duplicate_candidates_collapse_to_one_item(hub):
    project = hub.create("project", {"title": "Alpha", "status": "active"})
    hub.create(
        "memory",
        {"statement": "alpha confirmed", "kind": "semantic", "project_id": project["id"]},
    )
    hub.retriever = _Dup()
    contract = hub.get_context_contract(OWNER, "alpha", subject_ref=project["id"])
    statements = [item["body"].get("statement") for item in contract["memories"]]
    assert statements.count("alpha confirmed") == 1
    matches = [
        candidate
        for candidate in hub.last_compilation_trace["candidates"]
        if candidate["item_id"]
        and any(item["ref"]["id"] == candidate["item_id"] for item in contract["memories"])
    ]
    assert len(matches) == 1
    assert matches[0]["relevance"] == 0.9
    assert matches[0]["source_ref"]
    assert "signals" in matches[0]


def test_published_envelope_has_no_retrieval_candidate():
    schema = json.dumps(envelope_json_schema())
    assert "RetrievalCandidate" not in schema
    assert "finder_notes" not in schema
