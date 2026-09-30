#!/usr/bin/env python3
"""Build the publishable wheels (not pch-lab)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PUBLISH_PACKAGES = (
    "pch-core",
    "pch-archive",
    "pch-sdk",
    "pch-server",
)


def build(dist: Path, *, cwd: Path) -> None:
    dist.mkdir(parents=True, exist_ok=True)
    for package in PUBLISH_PACKAGES:
        result = subprocess.run(
            ["uv", "build", "--package", package, "--out-dir", str(dist)],
            cwd=cwd,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    cwd = Path.cwd()
    dist = Path(args[0] if args else cwd / "dist")
    build(dist, cwd=cwd)


if __name__ == "__main__":
    main()
