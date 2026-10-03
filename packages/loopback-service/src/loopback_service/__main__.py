from __future__ import annotations

import argparse
import ctypes
import ipaddress
import os
import select
import socket
import sys
from pathlib import Path

import uvicorn
from trust_kernel.vault.keys import announce_file_key

from loopback_service.rest.app import dev_app

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
        if (parent / "packages" / "loopback-service").is_dir():
            dirs = [
                parent / "packages" / "trust-kernel" / "src",
                parent / "packages" / "loopback-service" / "src",
                parent / "packages" / "agent-client" / "src",
                parent / "packages" / "portable-state" / "src",
            ]
            return [str(path) for path in dirs if path.is_dir()]
    return []


def inherited_listen_fd() -> int | None:
    if os.environ.get("LISTEN_FDS") != "1":
        return None
    pid = os.environ.get("LISTEN_PID")
    if pid is not None and pid != str(os.getpid()):
        return None
    return 3


def launchd_listen_fd() -> int | None:
    name = os.environ.get("PERSONAL_CONTEXT_LAUNCHD_SOCKET")
    if not name or sys.platform != "darwin":
        return None
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    libc.launch_activate_socket.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.POINTER(ctypes.c_int)),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    libc.launch_activate_socket.restype = ctypes.c_int
    fds = ctypes.POINTER(ctypes.c_int)()
    count = ctypes.c_size_t()
    rc = libc.launch_activate_socket(name.encode(), ctypes.byref(fds), ctypes.byref(count))
    if rc != 0 or count.value < 1:
        raise SystemExit(f"launchd socket {name} was not available")
    return int(fds[0])


def bind_and_wait(host: str, port: int) -> socket.socket:
    """Listen without opening the vault. Return after the first connection is queued."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(128)
    select.select([sock], [], [])
    return sock


def run_server(host: str, port: int, *, reload: bool, fd: int | None = None) -> None:
    if reload:
        uvicorn.run(
            "loopback_service.rest.app:dev_app",
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
    kwargs: dict[str, object] = {"host": host, "port": port, "log_level": "info"}
    if fd is not None:
        kwargs["fd"] = fd
    uvicorn.run(dev_app(), **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="personal-context-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PERSONAL_CONTEXT_PORT", "8765")))
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("PERSONAL_CONTEXT_DATA_DIR", str(Path.home() / ".personal-context")),
    )
    parser.add_argument("--reload", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--wake",
        action="store_true",
        help="Bind loopback and open the vault only after the first connection",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if not is_loopback_host(args.host):
        print(LOOPBACK_MSG)
        raise SystemExit(2)
    bind_host = "127.0.0.1" if args.host in {"::1", "[::1]"} else args.host
    os.environ["PERSONAL_CONTEXT_DATA_DIR"] = args.data_dir
    data_dir = Path(args.data_dir)
    announce_file_key(data_dir)
    held: socket.socket | None = None
    fd = inherited_listen_fd() or launchd_listen_fd()
    if args.wake and fd is None:
        held = bind_and_wait(bind_host, args.port)
        fd = held.fileno()
    run_server(bind_host, args.port, reload=args.reload, fd=fd)
    del held


if __name__ == "__main__":
    main()
