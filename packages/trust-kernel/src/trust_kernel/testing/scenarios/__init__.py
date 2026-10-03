from __future__ import annotations

import json
from pathlib import Path


def load_scenarios() -> list[dict]:
    root = Path(__file__).parent
    rows = []
    for path in sorted(root.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows
