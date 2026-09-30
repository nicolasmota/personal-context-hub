from ulid import ULID

PREFIXES = {
    "person": "per",
    "space": "spc",
    "profile": "prf",
    "preference": "pref",
    "project": "prj",
    "goal": "goal",
    "commitment": "cmt",
    "decision": "dec",
    "artifact": "art",
    "memory": "mem",
    "shared_state": "st",
    "connection": "con",
    "grant": "grant",
    "manifest": "man",
    "proposal": "prop",
    "conflict": "cnf",
    "action_intent": "act",
    "approval": "appr",
    "audit_event": "evt",
    "export": "exp",
    "import_staging": "imp",
    "vendor_import_batch": "vib",
    "event": "evt",
    "operational_proposal": "oprop",
    "relation": "rel",
    "relation_proposal": "rprop",
}


def new_id(kind: str) -> str:
    prefix = PREFIXES.get(kind, "obj")
    return f"{prefix}_{ULID()}"
