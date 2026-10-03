#!/usr/bin/env python3
"""Fail if git-tracked paths match the open-source secrets deny-list."""

from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path

# Deny-list tokens documented for tests and contributors:
# .env, google_oauth.json, .cursor/mcp.json, .personal-context, .personal-context-sim, .vault
DENY_SUFFIX_GLOBS = (
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.pca",
    "*.key",
)
DENY_BASENAMES = {
    ".env",
    "google_oauth.json",
}
DENY_BASENAME_PREFIXES = (".env.",)
DENY_PATH_SUFFIXES = (
    ".cursor/mcp.json",
)
DENY_SEGMENTS = (
    ".vault",
    ".personal-context",
    ".personal-context-sim",
)


def _repo_root() -> Path:
    override = os.environ.get("PERSONAL_CONTEXT_SECRETS_REPO")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1]


def _tracked_files(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        sys.exit(2)
    raw = result.stdout.split(b"\0")
    return [p.decode("utf-8", errors="replace") for p in raw if p]


def _basename_pairing_token(name: str) -> bool:
    lower = name.lower()
    if fnmatch.fnmatch(lower, "pairing_token*"):
        return True
    if fnmatch.fnmatch(lower, "*pairing*token*"):
        return True
    return False


def is_denied(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    if any(fnmatch.fnmatch(name, g) for g in DENY_SUFFIX_GLOBS):
        return True
    if name in DENY_BASENAMES:
        return True
    if any(name.startswith(p) for p in DENY_BASENAME_PREFIXES):
        return True
    if any(normalized == s or normalized.endswith("/" + s) for s in DENY_PATH_SUFFIXES):
        return True
    parts = normalized.split("/")
    if any(seg in DENY_SEGMENTS for seg in parts):
        return True
    if _basename_pairing_token(name):
        return True
    return False


def main() -> int:
    repo = _repo_root()
    matches = [p for p in _tracked_files(repo) if is_denied(p)]
    if matches:
        print("Tracked paths match secrets deny-list:")
        for path in matches:
            print(path)
        return 1
    print("OK: no tracked secrets deny-list paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
