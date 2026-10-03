from __future__ import annotations

from pathlib import Path

import pytest
from trust_kernel.service import Hub


@pytest.fixture
def hub(tmp_path: Path) -> Hub:
    h = Hub(tmp_path / "vault", plain=True)
    h.setup("Tester")
    yield h
    h.close()
