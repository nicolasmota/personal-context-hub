import json
import socket
import stat
from pathlib import Path

import pytest
from agent_client.service_cmd import (
    install_service,
    logs_service,
    status_service,
    uninstall_service,
)
from agent_client.service_units import render_launchd, render_systemd, render_windows


def test_login_definitions_are_local_and_do_not_reload():
    program = "/usr/local/bin/personal-context-server"
    data_dir = "/home/person/.personal-context"
    systemd = render_systemd(program, data_dir, 8765)
    launchd = render_launchd(program, data_dir, 8765)
    windows = render_windows(program, data_dir, 8765)
    for text in (systemd, launchd, windows):
        assert "127.0.0.1" in text
        assert "0.0.0.0" not in text
        assert "::" not in text
        assert "--no-reload" in text
        assert "WatchPaths" not in text
    assert "--reload\n" not in systemd
    assert "inetdCompatibility" not in launchd
    assert "--wake" in windows


def test_server_reload_defaults_off():
    source = Path("packages/loopback-service/src/loopback_service/__main__.py").read_text()
    assert 'add_argument("--reload"' in source
    assert "default=False" in source


def test_install_refuses_a_taken_port(tmp_path: Path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(1)
    try:
        with pytest.raises(SystemExit) as caught:
            install_service(
                data_dir=tmp_path / "vault",
                port=port,
                host="127.0.0.1",
                config_home=tmp_path / "config",
                program="/usr/bin/personal-context-server",
                platform="systemd-user",
                runner=_ok,
            )
        assert caught.value.code == 1
    finally:
        sock.close()
    assert not (tmp_path / "config").exists() or not any((tmp_path / "config").rglob("*"))


def test_second_install_is_one_definition(tmp_path: Path):
    data = tmp_path / "vault"
    data.mkdir()
    config = tmp_path / "config"
    kwargs = dict(
        data_dir=data,
        port=_free_port(),
        host="127.0.0.1",
        config_home=config,
        program="/usr/bin/personal-context-server",
        platform="systemd-user",
        runner=_ok,
    )
    first = install_service(**kwargs)
    second = install_service(**kwargs)
    units = list((config / "systemd" / "user").glob("personal-context.*"))
    assert first["installed"] is True
    assert second["installed"] is True
    assert len(units) == 2


def test_uninstall_missing_keeps_the_vault(tmp_path: Path):
    data = tmp_path / "vault"
    data.mkdir()
    (data / "vault.db").write_bytes(b"keep")
    result = uninstall_service(data_dir=data, config_home=tmp_path / "config", platform="systemd-user", runner=_ok)
    assert result == {"installed": False, "removed": False}
    assert (data / "vault.db").read_bytes() == b"keep"


def test_status_and_logs_hide_secrets(tmp_path: Path):
    data = tmp_path / "vault"
    data.mkdir()
    key = "ab" * 32
    (data / "vault.key").write_text(key)
    (data / "owner.token").write_text("secret-token")
    (data / "vault.key").chmod(stat.S_IRUSR | stat.S_IWUSR)
    config = tmp_path / "config"
    install_service(
        data_dir=data,
        port=_free_port(),
        host="127.0.0.1",
        config_home=config,
        program="/usr/bin/personal-context-server",
        platform="systemd-user",
        runner=_ok,
    )
    status = status_service(data_dir=data, config_home=config, platform="systemd-user", runner=_inactive)
    rendered = json.dumps(status)
    assert status["key_source"] == "file"
    assert status["state"] == "waiting"
    assert key not in rendered
    assert "secret-token" not in rendered
    text = logs_service(
        data_dir=data,
        config_home=config,
        platform="systemd-user",
        runner=lambda _args: _completed(f"opened {key} token secret-token\n"),
    )
    assert key not in text
    assert "secret-token" not in text
    assert "[redacted]" in text


def test_install_rejects_non_loopback(tmp_path: Path):
    with pytest.raises(SystemExit) as caught:
        install_service(
            data_dir=tmp_path,
            port=8765,
            host="0.0.0.0",
            config_home=tmp_path / "config",
            program="/usr/bin/personal-context-server",
            platform="systemd-user",
            runner=_ok,
        )
    assert caught.value.code == 2


def test_bridge_does_not_start_the_hub():
    source = Path("packages/agent-client/src/agent_client/mcp_bridge.py").read_text()
    assert "personal-context-server" not in source
    assert "subprocess" not in source


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _Completed:
    def __init__(self, text: str, code: int = 0) -> None:
        self.stdout = text
        self.returncode = code


def _completed(text: str, code: int = 0) -> _Completed:
    return _Completed(text, code)


def _ok(_args: list[str]) -> _Completed:
    return _completed("")


def _inactive(args: list[str]) -> _Completed:
    if "is-active" in args and args[-1].endswith(".service"):
        return _completed("inactive\n", 3)
    if "is-active" in args:
        return _completed("active\n")
    return _completed("")
