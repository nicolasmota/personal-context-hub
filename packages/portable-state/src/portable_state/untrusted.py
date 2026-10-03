from __future__ import annotations


def mark_untrusted(record: dict) -> dict:
    rec = dict(record)
    rec["untrusted"] = True
    if rec.get("authority") == "user_confirmed" and rec.get("type") != "memory":
        pass
    if rec.get("type") == "artifact":
        rec["untrusted"] = True
        rec["authority"] = rec.get("authority") or "source_imported"
    return rec
