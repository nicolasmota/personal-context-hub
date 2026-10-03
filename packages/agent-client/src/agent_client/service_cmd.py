from __future__ import annotations

import ipaddress
import os
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from trust_kernel.errors import VaultKeyError
from trust_kernel.vault.keys import key_storage, load_or_create_key

from agent_client.service_units import render_launchd, render_windows, systemd_units

Runner = Callable[[list[str]], subprocess.CompletedProcess[str] | object]


def install_service(
    *,
    data_dir: Path,
    port: int = 8765,
    host: str = "127.0.0.1",
    config_home: Path | None = None,
    program: str | None = None,
    platform: str | None = None,
    runner: Runner | None = None,
) -> dict:
    if not _loopback(host):
        print("The Hub is not a public server; it binds loopback only.", file=sys.stderr)
        raise SystemExit(2)
    resolved = program or _find_program()
    if resolved is None:
        print("personal-context-server was not found", file=sys.stderr)
        raise SystemExit(1)
    kind = platform or detect_platform()
    directory = definition_dir(kind, config_home)
    db = data_dir / "vault.db"
    if db.is_file() and db.stat().st_size > 0:
        try:
            load_or_create_key(data_dir)
        except VaultKeyError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
    if _port_taken(host, port) and not _installed(directory, kind):
        print(f"Port {port} is already in use. Not starting a second Hub.", file=sys.stderr)
        raise SystemExit(1)
    _write(kind, directory, resolved, str(data_dir), port)
    _enable(kind, directory, runner or _default_runner)
    return {"installed": True, "listen": f"127.0.0.1:{port}", "platform": kind}


def uninstall_service(
    *,
    data_dir: Path,
    config_home: Path | None = None,
    platform: str | None = None,
    runner: Runner | None = None,
) -> dict:
    kind = platform or detect_platform()
    directory = definition_dir(kind, config_home)
    if not _installed(directory, kind):
        return {"installed": False, "removed": False}
    _disable(kind, runner or _default_runner)
    for path in _definition_files(directory, kind):
        path.unlink(missing_ok=True)
    return {"installed": False, "removed": True}


def status_service(
    *,
    data_dir: Path,
    config_home: Path | None = None,
    platform: str | None = None,
    runner: Runner | None = None,
    port: int = 8765,
) -> dict:
    kind = platform or detect_platform()
    directory = definition_dir(kind, config_home)
    installed = _installed(directory, kind)
    state = "absent"
    if installed:
        state = "answering" if _service_active(kind, runner or _default_runner) else "waiting"
    return {
        "installed": installed,
        "state": state,
        "listen": f"127.0.0.1:{port}" if installed else None,
        "key_source": key_storage(data_dir),
    }


def logs_service(
    *,
    data_dir: Path,
    config_home: Path | None = None,
    platform: str | None = None,
    runner: Runner | None = None,
) -> str:
    kind = platform or detect_platform()
    text = _read_logs(kind, definition_dir(kind, config_home), runner or _default_runner)
    return redact(text, data_dir)


def redact(text: str, data_dir: Path) -> str:
    secrets: list[str] = []
    for name in ("vault.key", "owner.token"):
        path = data_dir / name
        if path.is_file():
            raw = path.read_text().strip()
            if raw:
                secrets.append(raw)
    env = os.environ.get("PERSONAL_CONTEXT_VAULT_KEY")
    if env:
        secrets.append(env)
    for secret in secrets:
        text = text.replace(secret, "[redacted]")
    return text


def detect_platform() -> str:
    if sys.platform == "darwin":
        return "launchd"
    if sys.platform == "win32":
        return "windows-task"
    return "systemd-user"


def definition_dir(platform: str, config_home: Path | None) -> Path:
    if platform == "systemd-user":
        base = config_home or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "systemd" / "user"
    if platform == "launchd":
        if config_home is not None:
            return config_home / "LaunchAgents"
        return Path.home() / "Library" / "LaunchAgents"
    if config_home is not None:
        return config_home / "PersonalContext"
    return Path.home() / "AppData" / "Roaming" / "PersonalContext"


def _loopback(host: str) -> bool:
    candidate = host.strip().strip("[]")
    if candidate.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _find_program() -> str | None:
    return shutil.which("personal-context-server")


def _port_taken(host: str, port: int) -> bool:
    sock = socket.socket()
    try:
        sock.bind((host, port))
    except OSError:
        return True
    finally:
        sock.close()
    return False


def _installed(directory: Path, platform: str) -> bool:
    return any(path.is_file() for path in _definition_files(directory, platform))


def _definition_files(directory: Path, platform: str) -> list[Path]:
    if platform == "systemd-user":
        return [directory / "personal-context.socket", directory / "personal-context.service"]
    if platform == "launchd":
        return [directory / "personal-context.plist"]
    return [directory / "PersonalContext.xml"]


def _write(platform: str, directory: Path, program: str, data_dir: str, port: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if platform == "systemd-user":
        for name, text in systemd_units(program, data_dir, port).items():
            (directory / name).write_text(text)
        return
    if platform == "launchd":
        (directory / "personal-context.plist").write_text(render_launchd(program, data_dir, port))
        return
    (directory / "PersonalContext.xml").write_text(render_windows(program, data_dir, port))


def _enable(platform: str, directory: Path, runner: Runner) -> None:
    if platform == "systemd-user":
        _run(runner, ["systemctl", "--user", "daemon-reload"])
        _run(runner, ["systemctl", "--user", "enable", "--now", "personal-context.socket"])
        return
    if platform == "launchd":
        plist = directory / "personal-context.plist"
        _run(runner, ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)])
        return
    xml = directory / "PersonalContext.xml"
    _run(runner, ["schtasks", "/Create", "/TN", "PersonalContext", "/XML", str(xml), "/F"])


def _disable(platform: str, runner: Runner) -> None:
    if platform == "systemd-user":
        runner(
            [
                "systemctl",
                "--user",
                "disable",
                "--now",
                "personal-context.socket",
                "personal-context.service",
            ]
        )
        return
    if platform == "launchd":
        runner(["launchctl", "bootout", f"gui/{os.getuid()}/personal-context"])
        return
    runner(["schtasks", "/Delete", "/TN", "PersonalContext", "/F"])


def _service_active(platform: str, runner: Runner) -> bool:
    if platform != "systemd-user":
        return False
    result = runner(["systemctl", "--user", "is-active", "personal-context.service"])
    return str(getattr(result, "stdout", "") or "").strip() == "active"


def _read_logs(platform: str, directory: Path, runner: Runner) -> str:
    if platform == "systemd-user":
        result = runner(
            ["journalctl", "--user", "-u", "personal-context.service", "-n", "80", "--no-pager"]
        )
        return str(getattr(result, "stdout", "") or "")
    if platform == "launchd":
        path = Path.home() / "Library" / "Logs" / "personal-context.log"
    else:
        path = directory / "personal-context.log"
    if not path.is_file():
        return ""
    return path.read_text()


def _run(runner: Runner, args: list[str]) -> object:
    result = runner(args)
    code = getattr(result, "returncode", 0)
    if code not in (0, None):
        detail = getattr(result, "stderr", "") or getattr(result, "stdout", "")
        print(detail or f"command failed: {' '.join(args)}", file=sys.stderr)
        raise SystemExit(1)
    return result


def _default_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)
