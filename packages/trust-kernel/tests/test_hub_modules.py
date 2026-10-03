"""Hub facade modules (019). Fails while Hub is still one service.py god file."""

from __future__ import annotations

from pathlib import Path

from trust_kernel.service import Hub

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "packages" / "trust-kernel" / "src" / "trust_kernel" / "service.py"
HUB = ROOT / "packages" / "trust-kernel" / "src" / "trust_kernel" / "hub"


def test_service_facade_has_no_plugin_pairing_or_capture_bodies() -> None:
    text = SERVICE.read_text(encoding="utf-8")
    assert "def mint_link" not in text
    assert "def create_plugin_installation" not in text
    assert "def capture_experience" not in text
    assert len(text.splitlines()) < 220


def test_hub_keeps_public_methods() -> None:
    assert callable(Hub.mint_link)
    assert callable(Hub.capture_experience)
    assert callable(Hub.evolve)
    assert not hasattr(Hub, "create_plugin_installation")


def test_named_domain_modules() -> None:
    pairing = (HUB / "pairing.py").read_text(encoding="utf-8")
    capture = (HUB / "capture.py").read_text(encoding="utf-8")
    evolution = (HUB / "evolution.py").read_text(encoding="utf-8")
    assert "def mint_link" in pairing
    assert "def capture_experience" in capture
    assert "def evolve" in evolution
    assert not (HUB / "plugins.py").exists()
