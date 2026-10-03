"""SC-003 / SC-005: community health files, README, templates, licenses, CI."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

PYPROJECTS = [
    ROOT / "packages" / "trust-kernel" / "pyproject.toml",
    ROOT / "packages" / "loopback-service" / "pyproject.toml",
    ROOT / "packages" / "agent-client" / "pyproject.toml",
    ROOT / "packages" / "eval-harness" / "pyproject.toml",
    ROOT / "packages" / "portable-state" / "pyproject.toml",
]


def test_license_file_is_mit() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text or "Permission is hereby granted" in text
    assert "WITHOUT WARRANTY" in text.upper() or "AS IS" in text


def test_package_licenses_are_mit() -> None:
    for path in PYPROJECTS:
        text = path.read_text(encoding="utf-8")
        assert 'license = "MIT"' in text or "license = { text = \"MIT\" }" in text, path


def test_required_community_docs_exist() -> None:
    for name in (
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
        "CITATION.cff",
    ):
        assert (ROOT / name).is_file(), name


def test_discoverability_files_exist() -> None:
    for rel in (
        "docs/_config.yml",
        "docs/index.md",
        "docs/llms.txt",
        "docs/llms-full.txt",
        "docs/robots.txt",
        "docs/assets/social-preview.png",
        "docs/_includes/head-custom.html",
        ".github/workflows/pages.yml",
    ):
        assert (ROOT / rel).is_file(), rel
    llms = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8")
    assert "get_context_contract" in llms
    assert "User-agent: GPTBot" in (ROOT / "docs" / "robots.txt").read_text(
        encoding="utf-8"
    )
    robots = (ROOT / "docs" / "robots.txt").read_text(encoding="utf-8")
    assert "Disallow: /" not in robots
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "Personal Context Hub" in citation
    assert "MIT" in citation
    assert "github.com/nicolasmota/personal-context-hub" in citation
    assert "github.com/nicolasmota/personal-context-hub" in llms
    config = (ROOT / "docs" / "_config.yml").read_text(encoding="utf-8")
    assert "baseurl: /personal-context-hub" in config


def test_checkout_launch_docs_match_venv() -> None:
    gs = (ROOT / "docs" / "getting-started.md").read_text(encoding="utf-8")
    assert "you can type `pch`" not in gs
    assert "uv run pch-sdk" in gs
    cli = (ROOT / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    assert "Simulator + catalog refresh" not in cli
    assert "dev_app() enables simulator" not in cli
    assert "uv tool upgrade personal-context-hub" not in cli
    assert "pin the uv tool" not in cli.lower()
    assert "uv run pch-sdk" in cli


def test_readme_front_door() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lower = text.lower()
    assert "local" in lower and ("~/.pch" in text or "your device" in lower)
    assert "mcp" in lower
    assert "make install" in text
    assert "uv run pch-sdk" in text
    assert "MIT" in text or "LICENSE" in text
    assert "CONTRIBUTING" in text
    assert "SECURITY" in text
    assert "CODE_OF_CONDUCT" in text or "Code of Conduct" in text
    assert "docs/assets/social-preview.png" not in text
    assert "docs/llms.txt" in text


def test_templates_warn_against_secrets() -> None:
    bug = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug.yml"
    pr = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
    assert bug.is_file()
    assert pr.is_file()
    for path in (bug, pr):
        text = path.read_text(encoding="utf-8").lower()
        hits = sum(
            1
            for token in ("vault", ".env", "oauth", "pairing", "mcp.json")
            if token in text
        )
        umbrella = "vault data, tokens, or oauth" in text or "oauth client" in text
        assert hits >= 3 or umbrella, path


def test_ci_workflow_runs_gates() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "check-secrets" in ci or "check_secrets" in ci
    assert re.search(r"\blint\b", ci)
    assert re.search(r"\btest\b", ci)
    assert "build_release.py" in ci
    assert "check_release.py" in ci


def test_gitignore_covers_hub_data_dirs() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".pch/" in text or ".pch" in text
    assert ".pch-sim/" in text or ".pch-sim" in text
    assert "pairing_token" in text
    assert "docs/VISION.md" in text
    assert "docs/ROADMAP.md" in text
    assert "docs/VISION-BAR.md" in text
    assert "specs/" in text
    assert ".specify/" in text
    assert "packages/loopback-service/src/loopback_service/static/" in text
    assert "packages/pcl-server/src/pcl_server/static/" not in text


def test_server_static_build_is_not_tracked() -> None:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "packages/loopback-service/src/loopback_service/static"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.returncode == 0, listed.stderr
    assert listed.stdout.strip() == ""


def test_speckit_local_dirs_are_not_tracked() -> None:
    for path in (".specify", "specs"):
        listed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", path],
            capture_output=True,
            text=True,
            check=False,
        )
        assert listed.returncode == 0, listed.stderr
        assert listed.stdout.strip() == "", path


def test_published_docs_do_not_link_local_speckit() -> None:
    blob = "github.com/nicolasmota/personal-context-hub/blob/"
    for rel in (
        "docs/index.md",
        "docs/llms.txt",
        "docs/README.md",
        "docs/architecture.md",
        "docs/develop.md",
        "docs/security.md",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert f"{blob}main/.specify" not in text, rel
        assert "](../.specify/" not in text, rel
