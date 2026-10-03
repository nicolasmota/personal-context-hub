from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from trust_kernel.context.budget import apply_budget
from trust_kernel.context.compiler import finalize_contract
from trust_kernel.context.selection import rank_established_first, select_for_purpose
from trust_kernel.errors import NotFound
from trust_kernel.ids import new_id
from trust_kernel.policy.evaluator import Decision, PolicyInput, PolicyResult, evaluate
from trust_kernel.policy.grants import grant_is_current
from trust_kernel.retrieval.ask import significant_tokens
from trust_kernel.retrieval.candidate import (
    RetrievalCandidate,
    candidate_from_row,
    dedupe_candidates,
    score_text,
)
from trust_kernel.retrieval.home import pick_home_project
from trust_kernel.retrieval.retriever import PurposeRetriever, TokenOverlapRetriever
from trust_kernel.retrieval.search import DefaultRanker, citations_for
from trust_kernel.schema.contract import (
    Citation,
    ConflictPair,
    ContextContract,
    ContextQuery,
    ContractItem,
    ItemRef,
    OmissionCategory,
    OmissionNote,
    RelationRef,
    ScopeSummary,
    SituationRef,
)
from trust_kernel.schema.grant import Grant
from trust_kernel.timeutil import now_iso, parse_instant, row_is_current
from trust_kernel.vault.objects import ObjectStore

MEMORY_INLINE_CAP = 10
CATEGORY_INLINE_CAP = 20
RELATION_CAP = 20

CAPTURE_HINTS = [
    "If they stated a durable preference, decision, goal, or life fact, call propose_memory; it is not canonical until they accept.",
    "If this package is empty or lists omissions, say so. Do not invent personal facts.",
]

_CANDIDATE_TYPES = (
    "project",
    "goal",
    "memory",
    "decision",
    "preference",
    "commitment",
    "shared_state",
)
_CANONICAL_TYPES = frozenset({"memory", "preference"})
_NON_CANONICAL_AUTHORITY = frozenset({"proposed", "agent_inferred"})

_GENERIC_PURPOSE_TOKENS = frozenset(
    {
        "matters",
        "now",
        "help",
        "current",
        "situation",
        "status",
        "today",
        "next",
        "please",
        "update",
        "continue",
        "planning",
        "plan",
    }
)

_OMISSION_LABELS = {
    OmissionCategory.SCOPE_NOT_GRANTED: "out-of-scope context withheld",
    OmissionCategory.CLASSIFICATION_CEILING: "items above classification ceiling withheld",
    OmissionCategory.CAPABILITY_MISSING: "items requiring missing capabilities withheld",
    OmissionCategory.POLICY_EXCLUSION: "policy-excluded context withheld",
    OmissionCategory.NOT_RELEVANT: "off-task context withheld",
    OmissionCategory.OVER_CAP: "items over package size withheld",
}


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _purpose_is_generic(tokens: list[str]) -> bool:
    return bool(tokens) and all(tok in _GENERIC_PURPOSE_TOKENS for tok in tokens)


def _meaningful_tokens(tokens: list[str]) -> list[str]:
    return [tok for tok in tokens if tok not in _GENERIC_PURPOSE_TOKENS]


def _overlaps_purpose(obj: dict[str, Any], tokens: list[str]) -> bool:
    if not tokens:
        return False
    blob = _blob(obj)
    return any(tok in blob for tok in tokens)


def _blob(obj: dict[str, Any]) -> str:
    return score_text(obj)


@dataclass
class CompilationTrace:
    candidates: list[RetrievalCandidate]
    contract: ContextContract
    find_ms: float


def _emit_candidates(
    retriever: PurposeRetriever, rows: list[dict[str, Any]], purpose: str
) -> list[RetrievalCandidate]:
    method = getattr(retriever, "find_candidates", None)
    if callable(method):
        found = list(method(rows, purpose))
    else:
        found = []
        for row in rows:
            relevance = float(retriever.relevance(score_text(row), purpose))
            if relevance <= 0:
                continue
            found.append(candidate_from_row(row, purpose, relevance))
        found.sort(key=lambda item: (-item.relevance, item.item_id))
    normalized: list[RetrievalCandidate] = []
    for item in found:
        if isinstance(item, RetrievalCandidate):
            normalized.append(item)
            continue
        normalized.append(RetrievalCandidate.model_validate(item))
    return dedupe_candidates(normalized)


def _relevance(retriever: PurposeRetriever, obj: dict[str, Any], purpose: str) -> float:
    return retriever.relevance(_blob(obj), purpose)


def _item_status(obj: dict[str, Any], moment: datetime) -> str:
    if obj.get("valid_until") and not row_is_current(obj, moment):
        return "expired"
    authority = str(obj.get("authority") or "")
    if authority in {"user_confirmed", "user"} and not obj.get("untrusted"):
        return "asserted"
    return "uncertain"


def _expired_item(obj: dict[str, Any]) -> ContractItem:
    subject = str(obj.get("key") or obj.get("subject_ref") or obj["id"])
    return ContractItem(
        ref=ItemRef(id=obj["id"], type=str(obj.get("type") or ""), summary=subject),
        body={"current": False},
        citation=_citations(obj),
        authority=str(obj.get("authority") or "user_confirmed"),
        confidence=obj.get("confidence"),
        freshness=_parse_dt(obj.get("updated_at")),
        untrusted=bool(obj.get("untrusted")),
        status="expired",
    )


def _summary(obj: dict[str, Any]) -> str:
    return str(
        obj.get("title") or obj.get("key") or obj.get("statement") or obj.get("name") or obj["id"]
    )


def _body(obj: dict[str, Any]) -> dict[str, Any]:
    kind = obj.get("type")
    if kind == "goal":
        keys = ("title", "outcome", "status", "horizon")
        return {k: obj.get(k) for k in keys if obj.get(k) is not None}
    if kind == "preference":
        body = {
            k: obj.get(k)
            for k in ("key", "value", "rationale", "condition")
            if obj.get(k) is not None
        }
        body["valid_from"] = obj.get("valid_from")
        body["valid_until"] = obj.get("valid_until")
        return body
    if kind == "memory":
        return {k: obj.get(k) for k in ("statement", "kind", "valid_from", "valid_until")}
    if kind == "decision":
        keys = ("title", "chosen_option", "alternatives", "rationale", "status")
        return {k: obj.get(k) for k in keys}
    if kind == "commitment":
        return {k: obj.get(k) for k in ("title", "status", "due_at") if obj.get(k) is not None}
    if kind == "shared_state":
        return {k: obj.get(k) for k in ("key", "value", "visibility", "expires_at")}
    return {k: v for k, v in obj.items() if k in ("title", "statement", "key", "value")}


def _citations(obj: dict[str, Any]) -> list[Citation]:
    raw = citations_for(obj)
    cites = [Citation(id=c.get("id") or obj["id"], role=c.get("role") or "source") for c in raw]
    self_cite = Citation(id=obj["id"], role="self", version=str(obj.get("version", 1)))
    if not any(c.id == obj["id"] for c in cites):
        cites.insert(0, self_cite)
    elif not cites:
        cites = [self_cite]
    return cites or [self_cite]


def _omission_category(result: PolicyResult) -> OmissionCategory:
    if result.decision == Decision.REDACT:
        return OmissionCategory.CLASSIFICATION_CEILING
    if "missing capability" in result.reason:
        return OmissionCategory.CAPABILITY_MISSING
    if "selector" in result.reason or "no active grants" in result.reason:
        return OmissionCategory.SCOPE_NOT_GRANTED
    return OmissionCategory.POLICY_EXCLUSION


def _cap_default(type_: str) -> str:
    if type_ in ("project", "goal", "decision"):
        return "project.read"
    if type_ == "commitment":
        return "commitment.read"
    if type_ in ("memory", "artifact", "event"):
        return "memory.retrieve"
    if type_ in ("profile", "preference", "person"):
        return "profile.read"
    return "project.read"


def _blank_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resource_project(obj: dict[str, Any]) -> str | None:
    if obj.get("type") == "project":
        return obj["id"]
    return obj.get("project_id")


def _situation_ref(project: dict[str, Any], goal: dict[str, Any] | None = None) -> SituationRef:
    phase = _blank_to_none(project.get("operational_phase"))
    step = _blank_to_none(project.get("current_step"))
    intent = _blank_to_none(project.get("situation_intent"))
    if goal:
        goal_phase = _blank_to_none(goal.get("operational_phase"))
        goal_step = _blank_to_none(goal.get("current_step"))
        goal_intent = _blank_to_none(goal.get("situation_intent"))
        if goal_phase:
            phase = goal_phase
        if goal_step:
            step = goal_step
        if goal_intent:
            intent = goal_intent
    return SituationRef(
        project_id=project["id"],
        title=project.get("title") or project["id"],
        status=str(project.get("status") or ""),
        operational_phase=phase,
        current_step=step,
        situation_intent=intent,
    )


def assemble_contract(
    store: ObjectStore,
    query: ContextQuery,
    *,
    actor: str,
    is_owner: bool,
    grants: list[Grant],
    cap_for: Callable[[str], str] | None = None,
    retriever: PurposeRetriever | None = None,
) -> ContextContract:
    return assemble_traced(
        store,
        query,
        actor=actor,
        is_owner=is_owner,
        grants=grants,
        cap_for=cap_for,
        retriever=retriever,
    ).contract


def assemble_traced(
    store: ObjectStore,
    query: ContextQuery,
    *,
    actor: str,
    is_owner: bool,
    grants: list[Grant],
    cap_for: Callable[[str], str] | None = None,
    retriever: PurposeRetriever | None = None,
) -> CompilationTrace:
    cap_for = cap_for or _cap_default
    retriever = retriever or TokenOverlapRetriever()
    rows: list[dict[str, Any]] = []
    for type_ in _CANDIDATE_TYPES:
        rows.extend(store.list(type_))
    started = time.perf_counter()
    found = _emit_candidates(retriever, rows, query.purpose)
    find_ms = (time.perf_counter() - started) * 1000
    tokens = significant_tokens(query.purpose)
    eval_at = parse_instant(query.as_of) if query.as_of else datetime.now(UTC)
    omission_counts: dict[OmissionCategory, int] = defaultdict(int)
    active_grants = [g for g in grants if grant_is_current(g, eval_at)]

    def decide(obj: dict[str, Any], resource_project: str | None) -> PolicyResult:
        if is_owner:
            return PolicyResult(Decision.ALLOW, "owner", [])
        return evaluate(
            PolicyInput(
                actor=actor,
                is_owner=False,
                grants=active_grants,
                resource_type=str(obj.get("type") or ""),
                resource_project=resource_project,
                classification=str(obj.get("classification") or "personal"),
                capability=cap_for(str(obj.get("type") or "")),
                purpose=query.purpose,
            )
        )

    def allowed(obj: dict[str, Any], resource_project: str | None) -> bool:
        blocked = {
            str(row.get("blocked_classification"))
            for row in store.list("disclosure_block")
            if row.get("blocked_classification")
        }
        if str(obj.get("classification") or "") in blocked:
            omission_counts[OmissionCategory.POLICY_EXCLUSION] += 1
            return False
        if (
            str(obj.get("type") or "") in _CANONICAL_TYPES
            and str(obj.get("authority") or "") in _NON_CANONICAL_AUTHORITY
        ):
            omission_counts[OmissionCategory.POLICY_EXCLUSION] += 1
            return False
        result = decide(obj, resource_project)
        if result.decision == Decision.ALLOW:
            return True
        omission_counts[_omission_category(result)] += 1
        return False

    projects = store.list("project")
    goals = store.list("goal")
    hinted: dict[str, Any] | None = None
    goal_overlay: dict[str, Any] | None = None
    if query.subject_ref:
        try:
            hinted = store.get(query.subject_ref)
        except NotFound:
            hinted = None
        if hinted and hinted.get("type") == "goal" and hinted.get("project_id"):
            goal_overlay = hinted
            try:
                hinted = store.get(hinted["project_id"])
            except NotFound:
                hinted = None
        if hinted and hinted.get("type") == "project":
            if not allowed(hinted, hinted["id"]):
                hinted = None
                goal_overlay = None

    scores: dict[str, float] = {}
    for project in projects:
        scores[project["id"]] = _relevance(retriever, project, query.purpose)
    for goal in goals:
        pid = goal.get("project_id")
        if pid:
            scores[pid] = scores.get(pid, 0) + _relevance(retriever, goal, query.purpose)
    for memory in store.list("memory"):
        pid = memory.get("project_id")
        if pid and not memory.get("tombstone") and row_is_current(memory, eval_at):
            scores[pid] = scores.get(pid, 0) + _relevance(retriever, memory, query.purpose)
    for decision in store.list("decision"):
        pid = decision.get("project_id")
        if pid:
            scores[pid] = scores.get(pid, 0) + _relevance(retriever, decision, query.purpose)

    selected: dict[str, Any] | None = None
    situation_ties: list[SituationRef] = []
    if hinted:
        selected = hinted
    elif tokens:
        best = max(scores.values(), default=0)
        tied = [p for p in projects if scores.get(p["id"], 0) == best and best > 0]
        in_scope = [p for p in tied if allowed(p, p["id"])]
        if len(in_scope) == 1:
            selected = in_scope[0]
        elif len(in_scope) > 1:
            situation_ties = [
                _situation_ref(p) for p in sorted(in_scope, key=lambda row: row["id"])
            ]

    if selected is None and not situation_ties and _purpose_is_generic(tokens):
        live = pick_home_project(projects)
        if live and allowed(live, live["id"]):
            selected = live
    situation = _situation_ref(selected, goal_overlay) if selected else None
    anchor_id = selected["id"] if selected else None

    def to_item(obj: dict[str, Any]) -> ContractItem:
        return ContractItem(
            ref=ItemRef(id=obj["id"], type=str(obj.get("type") or ""), summary=_summary(obj)),
            body=_body(obj),
            citation=_citations(obj),
            authority=str(obj.get("authority") or "user_confirmed"),
            confidence=obj.get("confidence"),
            freshness=_parse_dt(obj.get("updated_at")),
            untrusted=bool(obj.get("untrusted")),
            status=_item_status(obj, datetime.now(UTC)),
        )

    def take(
        rows: list[dict[str, Any]],
        cap: int,
        *,
        established_first: bool = False,
    ) -> list[ContractItem]:
        if established_first:
            ranked = rank_established_first(rows)
        else:
            ranked = DefaultRanker().rank(rows, query.purpose)
        chosen, overflow = apply_budget(ranked, cap)
        inline = [to_item(row) for row in chosen]
        if overflow:
            omission_counts[OmissionCategory.OVER_CAP] += overflow
        return inline

    cap = MEMORY_INLINE_CAP
    if query.max_items:
        cap = min(query.max_items, MEMORY_INLINE_CAP)
    cat_cap = CATEGORY_INLINE_CAP
    if query.max_items:
        cat_cap = min(query.max_items, CATEGORY_INLINE_CAP)

    goals_out: list[ContractItem] = []
    prefs_out: list[ContractItem] = []
    mems_out: list[ContractItem] = []
    decs_out: list[ContractItem] = []
    constraints_out: list[ContractItem] = []
    state_out: list[ContractItem] = []
    references: list[ItemRef] = []
    required_ids: set[str] = set()
    meaningful = _meaningful_tokens(tokens)

    if anchor_id:
        eval_project = anchor_id
        goal_rows = [
            g
            for g in store.list("goal", project_id=anchor_id)
            if g.get("status") not in ("done", "cancelled") and allowed(g, eval_project)
        ]
        pref_rows = [
            p
            for p in store.list("preference")
            if (p.get("project_id") in (None, anchor_id))
            and row_is_current(p, eval_at)
            and allowed(p, eval_project)
        ]
        mem_legal = [
            m
            for m in store.list("memory", project_id=anchor_id)
            if not m.get("tombstone") and row_is_current(m, eval_at) and allowed(m, eval_project)
        ]
        mem_rows, off_task = select_for_purpose(mem_legal, meaningful, _overlaps_purpose)
        if off_task:
            omission_counts[OmissionCategory.NOT_RELEVANT] += off_task
        dec_rows = [
            d
            for d in store.list("decision", project_id=anchor_id)
            if not d.get("tombstone") and row_is_current(d, eval_at) and allowed(d, eval_project)
        ]
        cmt_rows = [
            c
            for c in store.list("commitment", project_id=anchor_id)
            if c.get("status") not in ("done", "cancelled") and allowed(c, eval_project)
        ]
        now = now_iso()
        state_rows = []
        for s in store.list("shared_state"):
            if s.get("expires_at") and s["expires_at"] < now:
                continue
            if allowed(s, eval_project):
                state_rows.append(s)

        required_ids = {row["id"] for row in goal_rows + dec_rows + cmt_rows}
        goals_out = take(goal_rows, cat_cap)
        prefs_out = take(pref_rows, cat_cap)
        mems_out = take(mem_rows, cap, established_first=True)
        decs_out = take(dec_rows, cat_cap)
        constraints_out = take(cmt_rows, cat_cap)
        state_out = take(state_rows, cat_cap)

    moment = datetime.now(UTC)
    for type_ in ("preference", "memory"):
        for row in store.list(type_):
            if not row.get("valid_until") or row_is_current(row, moment):
                continue
            if row.get("tombstone"):
                continue
            if not allowed(row, anchor_id):
                continue
            state_out.append(_expired_item(row))

    relation_refs: list[RelationRef] = []
    if anchor_id:
        live = [row for row in store.list("relation") if row.get("status") == "live"]

        def incident(row: dict[str, Any], node_id: str) -> bool:
            return row.get("from_id") == node_id or row.get("to_id") == node_id

        hop0 = [row for row in live if incident(row, anchor_id)]
        neighbor_ids = {
            row["to_id"] if row.get("from_id") == anchor_id else row["from_id"] for row in hop0
        }
        hop0_ids = {row["id"] for row in hop0}
        hop1 = [
            row
            for row in live
            if row["id"] not in hop0_ids
            and (row.get("from_id") in neighbor_ids or row.get("to_id") in neighbor_ids)
        ]
        ranked = hop0 + hop1
        ranked.sort(key=lambda row: (str(row.get("relation_type") or ""), row["id"]))
        for rel in ranked[:RELATION_CAP]:
            try:
                src = store.get(rel["from_id"])
                dst = store.get(rel["to_id"])
            except NotFound:
                continue
            src_result = decide(src, _resource_project(src))
            dst_result = decide(dst, _resource_project(dst))
            if src_result.decision != Decision.ALLOW or dst_result.decision != Decision.ALLOW:
                denied = src_result if src_result.decision != Decision.ALLOW else dst_result
                omission_counts[_omission_category(denied)] += 1
                continue
            relation_refs.append(
                RelationRef(
                    id=rel["id"],
                    relation_type=str(rel["relation_type"]),
                    from_=ItemRef(
                        id=src["id"], type=str(src.get("type") or ""), summary=_summary(src)
                    ),
                    to=ItemRef(
                        id=dst["id"], type=str(dst.get("type") or ""), summary=_summary(dst)
                    ),
                )
            )

    present_ids = {
        item.ref.id
        for item in (
            *goals_out,
            *prefs_out,
            *mems_out,
            *decs_out,
            *constraints_out,
            *state_out,
        )
    }
    resolved_buckets: dict[str, tuple[list[ContractItem], int]] = {
        "goal": (goals_out, cat_cap),
        "preference": (prefs_out, cat_cap),
        "memory": (mems_out, cap),
        "decision": (decs_out, cat_cap),
        "commitment": (constraints_out, cat_cap),
        "shared_state": (state_out, cat_cap),
    }
    for conflict in store.list("state_conflict"):
        if conflict.get("status") != "closed" or conflict.get("resolution") == "unresolved":
            continue
        for claim_id in conflict.get("claim_ids") or []:
            if claim_id in present_ids:
                continue
            try:
                claim = store.get(claim_id)
            except NotFound:
                continue
            if not row_is_current(claim, eval_at):
                continue
            if not allowed(claim, _resource_project(claim)):
                continue
            bucket = resolved_buckets.get(str(claim.get("type") or ""))
            if bucket is None:
                continue
            items, limit = bucket
            if len(items) >= limit:
                omission_counts[OmissionCategory.OVER_CAP] += 1
                continue
            items.append(to_item(claim))
            present_ids.add(claim["id"])

    conflicts: list[ConflictPair] = []
    by_key: dict[str, list[str]] = defaultdict(list)
    for item in prefs_out:
        if item.body.get("condition"):
            continue
        key = str(item.body.get("key") or "")
        if key:
            by_key[key].append(item.ref.id)
    for _key, ids in by_key.items():
        if len(ids) >= 2:
            conflicts.append(ConflictPair(item_ids=sorted(ids), reason="preference_key_collision"))
    conflicts.sort(key=lambda c: c.item_ids[0])

    grant = None
    if is_owner:
        scope = ScopeSummary(
            grant_id="owner",
            selectors={},
            classification_ceiling="sensitive",
            capabilities=["*"],
            summary_human="owner",
        )
    elif active_grants:
        grant = active_grants[0]
        if anchor_id:
            for g in active_grants:
                if g.selectors.get("project") in (None, anchor_id):
                    grant = g
                    break
        scope = ScopeSummary(
            grant_id=grant.id,
            selectors=dict(grant.selectors),
            classification_ceiling=grant.classification_ceiling,
            capabilities=[str(c) for c in grant.capabilities],
            summary_human=grant.summary_human,
        )
    else:
        scope = ScopeSummary(
            grant_id="none",
            selectors={},
            classification_ceiling="public",
            capabilities=[],
            summary_human="no grant",
        )

    omissions = [
        OmissionNote(category=cat, label=_OMISSION_LABELS[cat], count=count)
        for cat, count in sorted(omission_counts.items(), key=lambda kv: kv[0].value)
        if count > 0
    ]

    presented = {item.ref.id for item in (*goals_out, *decs_out, *constraints_out)}
    sufficient = situation is not None and required_ids <= presented

    contract = finalize_contract(
        ContextContract(
            contract_id=new_id("contract"),
            purpose=query.purpose,
            situation=situation,
            candidates=situation_ties,
            goals=goals_out,
            preferences=prefs_out,
            memories=mems_out,
            decisions=decs_out,
            constraints=constraints_out,
            state=state_out,
            relations=relation_refs,
            references=references,
            conflicts=conflicts,
            granted_scope=scope,
            omissions=omissions,
            capture_hints=list(CAPTURE_HINTS),
            assembled_at=datetime.now(UTC),
            sufficient=sufficient,
            budget=query.max_items,
            onward_sharing="prohibited",
            training_use="prohibited",
            retention="session",
            policy_version="0.2",
            valid_until=(
                parse_instant(str(grant.expires_at))
                if grant is not None and grant.expires_at
                else None
            ),
        ),
        store,
        query,
    )
    return CompilationTrace(candidates=found, contract=contract, find_ms=find_ms)
