import json
from pathlib import Path

import pytest
from pch_sdk.__main__ import main


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
        ],
        capsys,
    )
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
