from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path

import uvicorn

from pch_server.rest.app import dev_app

LOOPBACK_MSG = "The Hub is not a public server; it binds loopback only."


def is_loopback_host(host: str) -> bool:
    candidate = host.strip().strip("[]")
    if candidate.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _reload_dirs() -> list[str]:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "packages" / "pch-server").is_dir():
            dirs = [
                parent / "packages" / "pch-core" / "src",
                parent / "packages" / "pch-server" / "src",
                parent / "packages" / "pch-sdk" / "src",
                parent / "packages" / "pch-archive" / "src",
            ]
            return [str(path) for path in dirs if path.is_dir()]
    return []


def run_server(host: str, port: int, *, reload: bool) -> None:
    if reload:
        uvicorn.run(
            "pch_server.rest.app:dev_app",
            factory=True,
            host=host,
            port=port,
            log_level="info",
            reload=True,
            reload_dirs=_reload_dirs() or None,
            reload_includes=["*.py", "*.toml"],
            reload_excludes=["*/static/*", "*/__pycache__/*", "*.pyc"],
        )
        return
    uvicorn.run(dev_app(), host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pch-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PCH_PORT", "8765")))
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("PCH_DATA_DIR", str(Path.home() / ".pch")),
    )
    parser.add_argument("--reload", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args(argv)
    if not is_loopback_host(args.host):
        print(LOOPBACK_MSG)
        raise SystemExit(2)
    bind_host = "127.0.0.1" if args.host in {"::1", "[::1]"} else args.host
    os.environ["PCH_DATA_DIR"] = args.data_dir
    run_server(bind_host, args.port, reload=args.reload)


if __name__ == "__main__":
    main()
