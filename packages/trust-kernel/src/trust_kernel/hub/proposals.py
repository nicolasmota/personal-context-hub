from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trust_kernel.errors import NotFound, ValidationFailed, VersionConflict
from trust_kernel.hub.const import OWNER
from trust_kernel.ids import new_id
from trust_kernel.memory.pipeline import evaluate_proposal
from trust_kernel.memory.sensitivity import blocks_auto_accept
from trust_kernel.schema.audit import EventKind
from trust_kernel.schema.memory import Memory
from trust_kernel.schema.proposal import OperationalProposal, ProposalStatus
from trust_kernel.timeutil import now_iso, parse_instant, row_is_current

_SENSITIVE = {"health", "finance", "financial", "legal", "intimate", "safety"}
_LESSON_LABEL = "origin:lesson"
_LESSON_DAYS = 7


class ProposalsMixin:
    def propose_memory(
        self,
        body: dict,
        actor: str,
        evidence_refs: list[str],
        expires_at: str | None = None,
    ) -> dict:
        if actor == OWNER:
            raise ValidationFailed("owner writes memories directly")
        incoming = dict(body)
        subject_key = str(incoming.pop("key", "") or incoming.pop("subject", "") or "").strip() or None
        risk_class = str(incoming.pop("risk_class", "sensitive") or "sensitive")
        if risk_class not in {"low", "sensitive"}:
            risk_class = "sensitive"
        reversible = bool(incoming.pop("reversible", False))
        proposed_value = incoming.pop("value", None)
        domain_class = str(incoming.pop("classification", "") or "")
        if domain_class in {"public", "personal", "private", "sensitive"}:
            incoming["classification"] = domain_class
            domain_class = ""
        mem_body = {**incoming}
        mem_body.setdefault("type", "memory")
        mem_body.setdefault("authority", "proposed")
        mem_body.setdefault("owner", self.person_id())
        mem_body.setdefault("id", new_id("memory"))
        mem_body.setdefault("space_id", "personal")
        mem_body.setdefault("created_at", now_iso())
        mem_body.setdefault("updated_at", now_iso())
        mem_body.setdefault("version", 1)
        mem_body.setdefault("labels", [])
        mem_body.setdefault("classification", "personal")
        mem_body.setdefault("source_refs", evidence_refs)
        mem_body.setdefault("confidence", 0.6)
        mem_body.setdefault("retention", {"mode": "until_revoked"})
        mem_body.setdefault("policy_tags", [])
        memory = Memory.model_validate(mem_body)
        existing = self.store.list("memory")
        proposal, conflicts = evaluate_proposal(memory, existing, actor, evidence_refs)
        if blocks_auto_accept(memory) and proposal.status == ProposalStatus.AUTO_ACCEPTED:
            proposal.status = ProposalStatus.PENDING
            proposal.policy_verdict = "needs_review"
        if evidence_refs and all(
            self._evidence_kind(evidence_id) == "agent_inference" for evidence_id in evidence_refs
        ):
            proposal.status = ProposalStatus.PENDING
            proposal.policy_verdict = "needs_review"
        if expires_at:
            parse_instant(expires_at)
        with self.engine.tx():
            p = proposal.model_dump(mode="json")
            p.update(
                {
                    "type": "proposal",
                    "owner": self.person_id(),
                    "labels": [],
                    "classification": "personal",
                    "created_at": proposal.created_at,
                    "updated_at": now_iso(),
                    "source_refs": evidence_refs,
                    "confidence": memory.confidence,
                    "authority": "proposed",
                    "retention": {"mode": "until_revoked"},
                    "policy_tags": [],
                    "version": 1,
                    "statement": memory.statement,
                    "expires_at": expires_at,
                    "subject_key": subject_key,
                    "previous_value": self._previous_for_subject(subject_key),
                    "risk_class": risk_class,
                    "reversible": reversible,
                    "domain_class": domain_class,
                    "proposed_value": proposed_value if proposed_value is not None else memory.statement,
                }
            )
            rule = self._matching_rule(p, evidence_refs)
            if rule is not None:
                self.evolve(
                    subject=str(p["subject_key"]),
                    value=p["proposed_value"],
                    reason="auto rule",
                    evidence_ids=list(evidence_refs),
                    rule_id=rule["id"],
                )
                p["status"] = ProposalStatus.AUTO_ACCEPTED.value
                p["rule_id"] = rule["id"]
            self.store.put(p)
            for c in conflicts:
                cp = c.model_dump(mode="json")
                cp.update(
                    {
                        "type": "conflict",
                        "owner": self.person_id(),
                        "labels": [],
                        "classification": "personal",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "source_refs": [],
                        "confidence": 1.0,
                        "authority": "user_confirmed",
                        "retention": {"mode": "until_revoked"},
                        "policy_tags": [],
                        "version": 1,
                    }
                )
                self.store.put(cp)
            self.ledger.append(EventKind.MEMORY_PROPOSED, actor, "memory proposed", [proposal.id])
        return {**p, "conflicts": [c.model_dump(mode="json") for c in conflicts]}

    def _previous_for_subject(self, subject_key: str | None):
        if not subject_key:
            return None
        current = [
            row for row in self._current_preferences(subject_key) if not row.get("declined")
        ]
        if not current:
            return None
        chosen = next((row for row in current if not str(row.get("condition") or "").strip()), current[0])
        return chosen.get("value")

    def _source_already_authoritative(self, subject_key: str, evidence_refs: list[str]) -> bool:
        current = [
            row for row in self._current_preferences(subject_key) if not row.get("declined")
        ]
        if not current or not evidence_refs:
            return False
        known_sources: set[str] = set()
        for evidence_id in self._citations(current[0]):
            try:
                row = self.get(evidence_id)
            except NotFound:
                continue
            if row.get("type") == "evidence" and row.get("kind") == "user_confirmed" and row.get("source"):
                known_sources.add(str(row["source"]))
        if not known_sources:
            return False
        for evidence_id in evidence_refs:
            try:
                row = self.get(evidence_id)
            except NotFound:
                return False
            if row.get("kind") != "user_confirmed":
                return False
            if str(row.get("source") or "") not in known_sources:
                return False
        return True

    def _matching_rule(self, proposal: dict, evidence_refs: list[str]) -> dict | None:
        key = proposal.get("subject_key")
        if not key or proposal.get("risk_class") != "low" or not proposal.get("reversible"):
            return None
        if proposal.get("conflict_ids"):
            return None
        domain = str(proposal.get("domain_class") or "")
        if domain in _SENSITIVE:
            return None
        flags = (proposal.get("proposed_memory") or {}).get("sensitivity_flags") or []
        if any(str(flag) in _SENSITIVE for flag in flags):
            return None
        if not self._source_already_authoritative(str(key), evidence_refs):
            return None
        for rule in self.store.list("auto_rule"):
            if rule.get("subject") == key and rule.get("risk_ceiling") == "low":
                return rule
        return None

    def save_auto_rule(self, subject: str) -> dict:
        key = str(subject or "").strip()
        if not key:
            raise ValidationFailed("subject is required")
        return self.create("auto_rule", {"subject": key, "risk_ceiling": "low"})

    def revise_proposal(self, proposal_id: str, edits: dict) -> dict:
        self.expire_due_proposals()
        with self.engine.tx():
            row = self.store.get(proposal_id)
            if row.get("status") != ProposalStatus.PENDING:
                raise ValidationFailed("only a pending proposal can be revised")
            memory = {**(row.get("proposed_memory") or {}), **edits}
            row["proposed_memory"] = memory
            if "statement" in edits:
                row["statement"] = edits["statement"]
            row["updated_at"] = now_iso()
            return self.store.put(row)

    def defer_proposal(self, proposal_id: str) -> dict:
        self.expire_due_proposals()
        with self.engine.tx():
            row = self.store.get(proposal_id)
            if row.get("status") != ProposalStatus.PENDING:
                raise ValidationFailed("only a pending proposal can be deferred")
            row["deferred_at"] = now_iso()
            return self.store.put(row)

    def decide_proposal(self, proposal_id: str, accept: bool, edits: dict | None = None) -> dict:
        self.expire_due_proposals()
        with self.engine.tx():
            p = self.store.get(proposal_id)
            if p.get("status") == ProposalStatus.EXPIRED:
                raise ValidationFailed("proposal expired")
            if accept:
                mem = p["proposed_memory"]
                origin = [
                    lab for lab in (mem.get("labels") or []) if str(lab).startswith("origin:")
                ]
                lesson_offer = _LESSON_LABEL in [str(lab) for lab in (p.get("labels") or [])]
                if edits:
                    mem = {**mem, **edits}
                if lesson_offer or edits:
                    mem["authority"] = "user_confirmed"
                else:
                    mem["authority"] = "agent_inferred"
                labels = list(mem.get("labels") or [])
                for lab in origin:
                    if lab not in labels:
                        labels.append(lab)
                mem["labels"] = labels
                mem["type"] = "memory"
                stored = None
                subject = mem.get("subject_ref")
                if subject:
                    at = datetime.now(UTC)
                    for row in self.store.list("memory"):
                        if row.get("subject_ref") == subject and row_is_current(row, at):
                            result = self.supersede(row["id"], mem)
                            stored = result["successor"]
                            break
                if stored is None:
                    mem.setdefault("id", new_id("memory"))
                    stored = self.store.put(mem)
                p["status"] = "accepted"
                self.store.put(p)
                self.ledger.append(
                    EventKind.MEMORY_ACCEPTED, OWNER, "proposal accepted", [stored["id"]]
                )
                return stored
            p["status"] = "rejected"
            self.store.put(p)
            self.ledger.append(EventKind.MEMORY_REJECTED, OWNER, "proposal rejected", [proposal_id])
            return p

    def expire_due_proposals(self, now: str | None = None) -> list[str]:
        moment = parse_instant(now) if now else datetime.now(UTC)
        expired: list[str] = []
        with self.engine.tx():
            for row in self.store.list("proposal"):
                if row.get("status") != ProposalStatus.PENDING:
                    continue
                deadline = row.get("expires_at")
                if not deadline or parse_instant(str(deadline)) > moment:
                    continue
                row["status"] = ProposalStatus.EXPIRED.value
                row["updated_at"] = now_iso()
                self.store.put(row)
                expired.append(row["id"])
        return expired

    def _evidence_kind(self, evidence_id: str) -> str | None:
        try:
            row = self.get(evidence_id)
        except NotFound:
            return None
        if row.get("type") != "evidence":
            return None
        return row.get("kind")

    def propose_operational_state(
        self,
        actor: str,
        target_id: str,
        operational_phase: str | None = None,
        current_step: str | None = None,
        situation_intent: str | None = None,
    ) -> dict:
        if actor == OWNER:
            raise ValidationFailed("owner writes operational state directly")
        if not target_id or not str(target_id).strip():
            raise ValidationFailed("target_id is required")
        target = self.store.get(target_id)
        if target.get("type") not in ("project", "goal"):
            raise ValidationFailed("target must be a project or goal")
        proposed = {
            "operational_phase": operational_phase,
            "current_step": current_step,
            "situation_intent": situation_intent,
        }
        self._assert_operational(proposed)
        created = now_iso()
        proposal = OperationalProposal(
            id=new_id("operational_proposal"),
            target_id=target_id,
            operational_phase=operational_phase,
            current_step=current_step,
            situation_intent=situation_intent,
            submitted_by=actor,
            status=ProposalStatus.PENDING,
            created_at=created,
        )
        with self.engine.tx():
            payload = proposal.model_dump(mode="json")
            payload.update(
                {
                    "type": "operational_proposal",
                    "owner": self.person_id(),
                    "labels": [],
                    "classification": "personal",
                    "updated_at": created,
                    "source_refs": [],
                    "confidence": 1.0,
                    "authority": "proposed",
                    "retention": {"mode": "until_revoked"},
                    "policy_tags": [],
                    "version": 1,
                }
            )
            stored = self.store.put(payload, new=True)
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                actor,
                "operational state proposed",
                [stored["id"], target_id],
            )
            return stored

    def list_operational_proposals(self, status: str | None = None) -> list[dict]:
        rows = self.store.list("operational_proposal")
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def decide_operational_proposal(self, proposal_id: str, accept: bool) -> dict:
        with self.engine.tx():
            proposal = self.store.get(proposal_id)
            if proposal.get("type") != "operational_proposal":
                raise NotFound(proposal_id)
            if proposal.get("status") != ProposalStatus.PENDING:
                raise VersionConflict("proposal already resolved")
            if accept:
                patch_body = {
                    key: proposal[key]
                    for key in ("operational_phase", "current_step", "situation_intent")
                    if proposal.get(key) is not None
                }
                if patch_body:
                    self.patch(proposal["target_id"], patch_body, None)
                proposal["status"] = ProposalStatus.ACCEPTED
                stored = self.store.put(proposal)
                self.ledger.append(
                    EventKind.OBJECT_WRITE,
                    OWNER,
                    "operational proposal accepted",
                    [proposal_id, proposal["target_id"]],
                )
                return stored
            proposal["status"] = ProposalStatus.REJECTED
            stored = self.store.put(proposal)
            self.ledger.append(
                EventKind.OBJECT_WRITE,
                OWNER,
                "operational proposal rejected",
                [proposal_id],
            )
            return stored

    def reconcile_lesson_offer(self, project_id: str) -> None:
        grouped: dict[str, list[str]] = {}
        for row in self.store.list("experience"):
            if row.get("project_id") != project_id:
                continue
            text = str(row.get("lesson") or "").strip()
            if not text:
                continue
            grouped.setdefault(text, []).append(row["id"])
        if len(grouped) == 1:
            lesson, episode_ids = next(iter(grouped.items()))
            if len(episode_ids) >= 2:
                self._upsert_lesson_offer(project_id, lesson, sorted(episode_ids))
                return
        if len(grouped) > 1:
            self._withdraw_lesson_offer(project_id)

    def _lesson_subject(self, project_id: str) -> str:
        return f"lesson:{project_id}"

    def _pending_lesson_offer(self, project_id: str) -> dict | None:
        key = self._lesson_subject(project_id)
        for row in self.store.list("proposal"):
            if row.get("subject_key") == key and row.get("status") == "pending":
                return row
        return None

    def _lesson_previous(self, project_id: str):
        key = self._lesson_subject(project_id)
        moment = datetime.now(UTC)
        for row in self.store.list("memory"):
            if row.get("subject_ref") == key and row_is_current(row, moment) and not row.get("tombstone"):
                return row.get("statement")
        return None

    def _withdraw_lesson_offer(self, project_id: str) -> None:
        pending = self._pending_lesson_offer(project_id)
        if pending is None:
            return
        pending["status"] = "superseded"
        pending["policy_verdict"] = "disagreement"
        self.store.put(pending)

    def _upsert_lesson_offer(self, project_id: str, lesson: str, episode_ids: list[str]) -> dict:
        pending = self._pending_lesson_offer(project_id)
        previous = self._lesson_previous(project_id)
        if pending is not None:
            memory = dict(pending.get("proposed_memory") or {})
            memory["statement"] = lesson
            memory["source_refs"] = episode_ids
            pending["statement"] = lesson
            pending["proposed_value"] = lesson
            pending["proposed_memory"] = memory
            pending["evidence_refs"] = episode_ids
            pending["source_refs"] = episode_ids
            pending["previous_value"] = previous
            return self.store.put(pending)
        now = now_iso()
        expires = (datetime.now(UTC) + timedelta(days=_LESSON_DAYS)).replace(microsecond=0)
        expires_at = expires.isoformat().replace("+00:00", "Z")
        memory = {
            "id": new_id("memory"),
            "type": "memory",
            "space_id": "personal",
            "owner": self.person_id(),
            "kind": "semantic",
            "statement": lesson,
            "subject_ref": self._lesson_subject(project_id),
            "project_id": project_id,
            "authority": "proposed",
            "labels": [_LESSON_LABEL],
            "classification": "personal",
            "source_refs": episode_ids,
            "confidence": 1.0,
            "retention": {"mode": "until_revoked"},
            "policy_tags": [],
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "valid_from": now,
            "valid_until": None,
            "never_true": False,
        }
        proposal = {
            "id": new_id("proposal"),
            "type": "proposal",
            "space_id": "personal",
            "owner": self.person_id(),
            "labels": [_LESSON_LABEL],
            "classification": "personal",
            "created_at": now,
            "updated_at": now,
            "source_refs": episode_ids,
            "confidence": 1.0,
            "authority": "proposed",
            "retention": {"mode": "until_revoked"},
            "policy_tags": [],
            "version": 1,
            "statement": lesson,
            "proposed_memory": memory,
            "evidence_refs": episode_ids,
            "submitted_by": OWNER,
            "status": "pending",
            "policy_verdict": "needs_review",
            "conflict_ids": [],
            "expires_at": expires_at,
            "subject_key": self._lesson_subject(project_id),
            "previous_value": previous,
            "risk_class": "sensitive",
            "reversible": False,
            "proposed_value": lesson,
        }
        stored = self.store.put(proposal, new=True)
        self.ledger.append(EventKind.MEMORY_PROPOSED, OWNER, "lesson offered", [stored["id"]])
        return stored
