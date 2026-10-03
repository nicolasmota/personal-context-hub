import subprocess
import sys
from pathlib import Path


def test_module_entry_mcp_bridge_help(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "-m", "pch_sdk", "mcp-bridge", "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
