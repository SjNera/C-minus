"""Packaging smoke test for the optional gcc checker entry point."""

import subprocess
import sys
import sysconfig
from pathlib import Path


def test_gcc_checker_console_entry_point_resolves(tmp_path: Path) -> None:
    script_name = "cminus-check.exe" if sys.platform == "win32" else "cminus-check"
    script = Path(sysconfig.get_path("scripts")) / script_name
    result = subprocess.run(
        [str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
    assert result.stderr == ""
