from __future__ import annotations


def render_systemd(program: str, data_dir: str, port: int) -> str:
    units = systemd_units(program, data_dir, port)
    return "\n".join(units.values())


def systemd_units(program: str, data_dir: str, port: int) -> dict[str, str]:
    socket = (
        "[Socket]\n"
        f"ListenStream=127.0.0.1:{port}\n"
        "\n"
        "[Install]\n"
        "WantedBy=sockets.target\n"
    )
    service = (
        "[Service]\n"
        f"ExecStart={program} --no-reload --host 127.0.0.1 --port {port} --data-dir {data_dir}\n"
    )
    return {"personal-context.socket": socket, "personal-context.service": service}


def render_launchd(program: str, data_dir: str, port: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<plist version="1.0"><dict>\n'
        "<key>Label</key><string>personal-context</string>\n"
        "<key>ProgramArguments</key><array>\n"
        f"<string>{program}</string>\n"
        "<string>--no-reload</string>\n"
        "<string>--host</string><string>127.0.0.1</string>\n"
        f"<string>--port</string><string>{port}</string>\n"
        f"<string>--data-dir</string><string>{data_dir}</string>\n"
        "</array>\n"
        "<key>Sockets</key><dict><key>Listeners</key><dict>\n"
        "<key>SockNodeName</key><string>127.0.0.1</string>\n"
        f"<key>SockServiceName</key><string>{port}</string>\n"
        "</dict></dict>\n"
        "<key>EnvironmentVariables</key><dict>\n"
        "<key>PERSONAL_CONTEXT_LAUNCHD_SOCKET</key><string>Listeners</string>\n"
        "</dict>\n"
        "</dict></plist>\n"
    )


def render_windows(program: str, data_dir: str, port: int) -> str:
    arguments = f"--no-reload --wake --host 127.0.0.1 --port {port} --data-dir {data_dir}"
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        "<Task><Actions><Exec>\n"
        f"<Command>{program}</Command>\n"
        f"<Arguments>{arguments}</Arguments>\n"
        "</Exec></Actions></Task>\n"
    )
