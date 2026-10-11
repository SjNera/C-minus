"""CLI option handling and the installed/module entry points."""

import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

from cminus import __version__
from cminus.main import main


def test_explicit_argv_is_independent_of_process_arguments(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["cminus", "--unknown"])
    assert main([]) == 0
    output = capsys.readouterr()
    assert "C-Minus" in output.out
    assert output.err == ""


def test_version_exits_successfully_without_running_pipeline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0
    output = capsys.readouterr()
    assert output.out == f"cminus {__version__}\n"
    assert output.err == ""


def test_help_lists_available_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    output = capsys.readouterr()
    assert "usage: cminus" in output.out
    assert "--help" in output.out and "--version" in output.out
    assert "pipeline not wired" not in output.out
    assert output.err == ""


@pytest.mark.parametrize("argv", [["--unknown"]])
def test_unsupported_arguments_report_usage_on_stderr(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        main(argv)
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "usage: cminus" in output.err
    assert "unrecognized arguments" in output.err
    assert argv[0] in output.err


@pytest.mark.parametrize("entry_point", ["module", "console"])
@pytest.mark.parametrize(
    "program,module",
    [("cminus", "cminus"), ("cminus-check", "cminus.extras.gcc_equivalence")],
)
def test_version_entry_points_work_outside_the_repository(
    entry_point: str,
    program: str,
    module: str,
    tmp_path: Path,
) -> None:
    if entry_point == "module":
        command = [sys.executable, "-m", module, "--version"]
    else:
        script_name = program + (".exe" if sys.platform == "win32" else "")
        script = Path(sysconfig.get_path("scripts")) / script_name
        command = [str(script), "--version"]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{program} {__version__}\n"
    assert result.stderr == ""


def test_module_entry_point_propagates_argument_errors(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "cminus", "--unknown"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "unrecognized arguments: --unknown" in result.stderr
