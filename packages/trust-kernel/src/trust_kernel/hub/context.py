from __future__ import annotations

from pydantic import ValidationError

from pch_core.errors import NotFound, PolicyDenied, Revoked, ValidationFailed
from pch_core.hub.const import OWNER
from pch_core.policy.evaluator import PolicyInput, evaluate
from pch_core.retrieval.ask import compose as compose_ask
from pch_core.retrieval.ask import retrieve as retrieve_ask
from pch_core.retrieval.briefs import project_brief
from pch_core.retrieval.contract import assemble_traced
from pch_core.retrieval.home import HOME_PURPOSE, pick_home_project
from pch_core.schema.audit import EventKind
from pch_core.schema.contract import ContextQuery
from pch_core.schema.grant import GrantStatus


class ContextMixin:
    def ask(
        self,
        question: str,
        *,
        actor: str = OWNER,
        purpose: str | None = None,
    ) -> dict:
        rows = retrieve_ask(self.engine, question)
        grants = self.grants_for(actor) if actor != OWNER else []
        kept = []
        notices: list[str] = []
        for row in rows:
            result = evaluate(
                PolicyInput(
                    actor=actor,
                    is_owner=actor == OWNER,
                    grants=grants,
                    resource_type=row.get("type", ""),
                    resource_project=row.get("project_id"),
                    classification=row.get("classification", "personal"),
                    capability=self._cap_for(row.get("type", "")),
                    purpose=purpose or "personal_question",
                )
            )
            if result.decision.value == "allow":
                kept.append(row)
            else:
                notices.extend(result.redactions or [result.reason])
        out = compose_ask(kept)
        if notices and not out["citations"]:
            existing_notices = list(out.get("notices") or [])
            out["notices"] = list(dict.fromkeys([*existing_notices, *notices]))
        self.ledger.append(
            EventKind.CONTEXT_DISCLOSE,
            actor,
            f"ask {question!r}",
            [c["id"] for c in out["citations"]],
        )
        return out

    def _cap_for(self, type_: str) -> str:
        if type_ in ("project", "goal", "decision"):
            return "project.read"
        if type_ == "commitment":
            return "commitment.read"
        if type_ in ("memory", "artifact", "event"):
            return "memory.retrieve"
        if type_ in ("profile", "preference", "person"):
            return "profile.read"
        return "project.read"

    def brief(self, project_id: str, actor: str = OWNER) -> dict:
        project = self.store.get(project_id)
        related = self.store.list(project_id=project_id)
        if actor != OWNER:
            filtered = self.search("", project_id=project_id, actor=actor)["results"]
            related = filtered
        return project_brief(project, related)

    def record_contract_refusal(self, actor: str, purpose: str) -> None:
        self.ledger.append(
            EventKind.CONTEXT_CONTRACT,
            actor,
            f"contract refused {purpose!r}",
            extra={
                "contract_id": None,
                "purpose": purpose,
                "status": "refused",
                "situation": None,
                "item_refs": [],
                "omission_categories": [],
            },
        )

    def get_context_contract(
        self,
        actor: str,
        purpose: str,
        subject_ref: str | None = None,
        max_items: int | None = None,
        as_of: str | None = None,
    ) -> dict:
        try:
            query = ContextQuery(
                purpose=purpose, subject_ref=subject_ref, max_items=max_items, as_of=as_of
            )
        except ValidationError as exc:
            loc = ""
            errs = exc.errors() if hasattr(exc, "errors") else []
            if errs:
                loc = ".".join(str(p) for p in errs[0].get("loc", ()))
            if loc == "as_of" or "as_of" in str(exc):
                raise ValidationFailed("as_of is invalid") from exc
            raise ValidationFailed("purpose is required") from exc
        if actor != OWNER:
            conn = self.store.get(actor)
            if conn.get("status") == "revoked":
                self.record_contract_refusal(actor, query.purpose)
                raise Revoked()
            grants = self.grants_for(actor)
            if not any(g.status == GrantStatus.ACTIVE for g in grants):
                self.record_contract_refusal(actor, query.purpose)
                raise PolicyDenied("no active grants")
        else:
            grants = []
        traced = assemble_traced(
            self.store,
            query,
            actor=actor,
            is_owner=actor == OWNER,
            grants=grants,
            cap_for=self._cap_for,
            retriever=getattr(self, "retriever", None),
        )
        self.last_compilation_trace = {
            "candidates": [item.model_dump(mode="json") for item in traced.candidates],
            "find_ms": traced.find_ms,
        }
        contract = traced.contract
        item_refs = []
        for section in (
            contract.goals,
            contract.preferences,
            contract.memories,
            contract.decisions,
            contract.constraints,
            contract.state,
        ):
            for item in section:
                item_refs.append({"id": item.ref.id, "type": item.ref.type})
        extra = {
            "contract_id": contract.contract_id,
            "purpose": contract.purpose,
            "status": "issued",
            "situation": contract.situation.project_id if contract.situation else None,
            "item_refs": item_refs,
            "omission_categories": [
                {"category": o.category.value, "count": o.count} for o in contract.omissions
            ],
        }
        self.ledger.append(
            EventKind.CONTEXT_CONTRACT,
            actor,
            f"contract {query.purpose!r}",
            [r["id"] for r in item_refs],
            extra=extra,
        )
        self._store_disclosure(actor, contract)
        return contract.model_dump(mode="json", by_alias=True)

    def _store_disclosure(self, actor: str, contract) -> None:
        item_ids: list[str] = []
        evidence_ids: list[str] = []
        sections = (
            contract.goals,
            contract.preferences,
            contract.memories,
            contract.decisions,
            contract.constraints,
            contract.state,
        )
        for section in sections:
            for item in section:
                item_ids.append(item.ref.id)
                for cite in item.citation:
                    evidence_ids.append(cite.id)
                try:
                    row = self.store.get(item.ref.id)
                except NotFound:
                    row = None
                if row:
                    evidence_ids.extend(str(ref) for ref in (row.get("source_refs") or []))
        self.create(
            "disclosure_receipt",
            {
                "contract_id": contract.contract_id,
                "connection_id": actor,
                "purpose": contract.purpose,
                "item_ids": item_ids,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "omissions": [note.model_dump(mode="json") for note in contract.omissions],
                "valid_until": contract.valid_until.isoformat() if contract.valid_until else None,
            },
        )

    def withhold_category(self, classification: str) -> dict:
        name = str(classification or "").strip()
        if not name:
            raise ValidationFailed("classification is required")
        return self.create("disclosure_block", {"blocked_classification": name})

    def current_situation(self) -> dict:
        project = pick_home_project(self.list("project"))
        if project is None:
            return {"project": None, "contract": None}
        return {
            "project": project,
            "contract": self.get_context_contract(OWNER, HOME_PURPOSE, subject_ref=project["id"]),
        }

    def owner_capture(self, statement: str, *, title: str | None = None) -> dict:
        fact = str(statement or "").strip()
        label = str(title).strip() if title is not None else ""
        label = label or None
        if not fact:
            raise ValidationFailed("a durable fact is required")
        with self.engine.tx():
            project = pick_home_project(self.list("project"))
            if project is None:
                if not label:
                    raise ValidationFailed("a situation title is required when nothing is in play")
                project = self.create("project", {"title": label, "status": "active"}, OWNER)
            memory = self.create(
                "memory",
                {"statement": fact, "kind": "semantic", "project_id": project["id"]},
                OWNER,
            )
        return {"project": project, "memory": memory}
