from __future__ import annotations

import argparse
from pathlib import Path


def verify_roundtrip(src: Path, dst: Path) -> int:
    from pch_core.service import Hub

    a = Hub(src, plain=True)
    b = Hub(dst, plain=True)
    types = ("project", "goal", "commitment", "decision", "memory", "preference", "artifact", "profile")
    ok = True
    for t in types:
        sa = sorted((r.get("id"), r.get("authority"), r.get("classification")) for r in a.list(t))
        sb = sorted((r.get("id"), r.get("authority"), r.get("classification")) for r in b.list(t))
        if sa != sb:
            print(f"mismatch {t}: {len(sa)} vs {len(sb)}")
            ok = False
    a.close()
    b.close()
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pch-archive")
    sub = parser.add_subparsers(dest="cmd")
    rt = sub.add_parser("verify-roundtrip")
    rt.add_argument("src")
    rt.add_argument("dst")
    args = parser.parse_args(argv)
    if args.cmd == "verify-roundtrip":
        raise SystemExit(verify_roundtrip(Path(args.src), Path(args.dst)))
    parser.print_help()


if __name__ == "__main__":
    main()
