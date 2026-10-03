# Replication rule

This repository does not copy the vault between devices and does not add a hosted replica.

A future product that copies the governed record must:

- keep both edits when they conflict;
- not treat clock order as authority;
- not treat the later write as the winner;
- carry evidence, decisions, grants, revocations, and disclosure receipts, not only the materialized rows.
