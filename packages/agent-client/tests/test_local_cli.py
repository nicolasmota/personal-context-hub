import json
from pathlib import Path

import pytest
from agent_client.__main__ import main
from agent_client.local_cli import _hub


def _run(argv: list[str], capsys) -> dict:
    main(argv)
    return json.loads(capsys.readouterr().out)


def test_local_loop(tmp_path: Path, capsys):
    data = str(tmp_path / "vault")
    owner = _run(["vault-init", "--data-dir", data, "--name", "Synthetic"], capsys)
    assert owner["owner_id"]
    experience = _run(
        [
            "experience-add",
            "--data-dir",
            data,
            "--action",
            "noted a weekday exception",
            "--context",
            "dinner",
            "--outcome",
            "recorded",
            "--at",
            "2026-09-29T12:00:00Z",
            "--provenance",
            "owner",
            "--project",
            "prj_demo",
        ],
        capsys,
    )
    opened = _hub(data)
    try:
        assert opened.get(experience["id"])["project_id"] == "prj_demo"
    finally:
        opened.close()
    evidence = _run(
        [
            "evidence-add",
            "--data-dir",
            data,
            "--kind",
            "user_confirmed",
            "--source",
            "owner",
            "--authority",
            "the person",
            "--at",
            "2026-09-29T12:00:00Z",
            "--statement",
            "weekdays differ",
            "--confidence",
            "1",
            "--verification",
            "verified",
        ],
        capsys,
    )
    evolved = _run(
        [
            "evolve",
            "--data-dir",
            data,
            "--subject",
            "food.spicy",
            "--value",
            "mild",
            "--condition",
            "weekdays",
            "--reason",
            "conditional exception",
            "--experience",
            experience["id"],
            "--evidence",
            evidence["id"],
        ],
        capsys,
    )
    assert evolved["transition_id"]
    contract = _run(
        ["compile", "--data-dir", data, "--purpose", "plan dinner this week", "--budget", "8"],
        capsys,
    )
    assert contract["budget"] == 8
    assert contract["purpose"] == "plan dinner this week"
    dest = str(tmp_path / "state.pca")
    exported = _run(
        ["archive-export", "--data-dir", data, "--dest", dest, "--passphrase", "test"],
        capsys,
    )
    assert exported["pca_version"] == "0.2.0"
    other = str(tmp_path / "imported")
    imported = _run(
        ["archive-import", "--data-dir", other, "--src", dest, "--passphrase", "test"],
        capsys,
    )
    assert imported["count"] > 0


def test_agent_inference_evolve_is_refused(tmp_path: Path, capsys):
    data = str(tmp_path / "vault")
    _run(["vault-init", "--data-dir", data, "--name", "Synthetic"], capsys)
    _run(
        [
            "evolve",
            "--data-dir",
            data,
            "--subject",
            "food.spicy",
            "--value",
            "hot",
            "--reason",
            "owner baseline",
        ],
        capsys,
    )
    evidence = _run(
        [
            "evidence-add",
            "--data-dir",
            data,
            "--kind",
            "agent_inference",
            "--source",
            "agent",
            "--authority",
            "agent",
            "--at",
            "2026-09-29T12:00:00Z",
            "--statement",
            "they changed",
            "--verification",
            "unverified",
        ],
        capsys,
    )
    with pytest.raises(SystemExit):
        main(
            [
                "evolve",
                "--data-dir",
                data,
                "--subject",
                "food.spicy",
                "--value",
                "mild",
                "--reason",
                "agent guess",
                "--evidence",
                evidence["id"],
            ]
        )


def test_consent_commands(tmp_path: Path, capsys):
    data = str(tmp_path / "vault")
    main(["vault-init", "--data-dir", data, "--name", "Synthetic"])
    capsys.readouterr()
    link = _run(["link", "--data-dir", data, "--name", "Cursor"], capsys)
    listed = _run(["connections", "--data-dir", data], capsys)
    assert listed["connections"][0]["id"] == link["connection_id"]
    granted = _run(
        [
            "grant",
            "--data-dir",
            data,
            "--connection",
            link["connection_id"],
            "--preset",
            "read_active_projects",
        ],
        capsys,
    )
    assert granted["summary_human"]
    revoked = _run(
        ["revoke", "--data-dir", data, "--connection", link["connection_id"]],
        capsys,
    )
    assert revoked["status"] == "revoked"
    src = tmp_path / "memory.json"
    src.write_text('[{"content": "Likes quiet mornings"}]', encoding="utf-8")
    imported = _run(
        ["import-memories", "--data-dir", data, "--src", str(src), "--provider", "chatgpt"],
        capsys,
    )
    assert imported["imported"] == 1
    pending = _run(["proposals", "--data-dir", data, "list"], capsys)
    assert pending["proposals"] == []
    token = _run(["token", "--data-dir", data], capsys)
    assert token["owner_token"]
    assert (tmp_path / "vault" / "owner.token").read_text(encoding="utf-8") == token["owner_token"]
