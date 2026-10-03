#!/usr/bin/env python3
"""Inspect dist/ wheels before publish."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

EXPECTED = [
    "trust_kernel",
    "portable_state",
    "agent_client",
    "loopback_service",
]


def _wheels(dist: Path) -> list[Path]:
    return sorted(dist.glob("*.whl"))


def _dist_name(wheel: Path) -> str:
    return wheel.name.split("-")[0]


def _version(wheel: Path) -> str:
    return wheel.name.split("-")[1]


def _read(wheel: Path, suffix: str) -> str | None:
    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith(suffix):
                return zf.read(name).decode("utf-8")
    return None


def check(dist: Path) -> list[str]:
    errors: list[str] = []
    wheels = _wheels(dist)
    names = [_dist_name(w) for w in wheels]
    if sorted(names) != sorted(EXPECTED):
        errors.append(f"expected wheels {EXPECTED}, got {names}")
        return errors
    versions = {_version(w) for w in wheels}
    if len(versions) != 1:
        errors.append(f"version mismatch: {sorted(versions)}")
    version = next(iter(versions))
    by_name = {_dist_name(w): w for w in wheels}

    siblings = {
        "portable_state": ["trust-kernel"],
        "agent_client": ["trust-kernel", "portable-state"],
        "loopback_service": ["trust-kernel", "portable-state", "agent-client"],
    }
    for dist_name, required in siblings.items():
        meta = _read(by_name[dist_name], "METADATA") or ""
        for dep in required:
            if not any(
                line.startswith("Requires-Dist:") and dep in line and f"=={version}" in line
                for line in meta.splitlines()
            ):
                errors.append(f"{dist_name} missing pin {dep}=={version}")
    return errors


def main(argv: list[str] | None = None) -> None:
    dist = Path((argv or sys.argv[1:])[0] if (argv or sys.argv[1:]) else "dist")
    errors = check(dist)
    if errors:
        for err in errors:
            print(err)
        raise SystemExit(1)
    print(f"ok: {len(_wheels(dist))} wheels in {dist}")


if __name__ == "__main__":
    main()
