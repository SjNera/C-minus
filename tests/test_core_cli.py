"""CLI translation, execution, inspection, and failure behavior."""

from pathlib import Path
import subprocess
import sys

import pytest

from cminus.extras.gcc_equivalence import main as checker_main
from cminus.extras.gcc_equivalence import Comparison
from cminus.main import main


def test_translation_and_all_inspection_flags_use_separate_streams(tmp_path, capsys):
    source = tmp_path / "program.c"
    source.write_text("int main(void) { int x=3; return x; }")
    assert (
        main(
            [
                str(source),
                "--dump-tokens",
                "--dump-ast",
                "--dump-symbols",
                "--verbose-passes",
            ]
        )
        == 0
    )
    output = capsys.readouterr()
    compile(output.out, "generated.py", "exec")
    assert "Tokens:" in output.err and "AST:" in output.err and "Symbols:" in output.err
    assert "binding_id=" in output.err and "resolved_type='int'" in output.err
    assert output.err.count("[cminus]") == 4


def test_output_file_and_run_from_another_directory(tmp_path):
    source = tmp_path / "program.c"
    script = tmp_path / "program.py"
    source.write_text(
        '#include <stdio.h>\nint main(void) { printf("ok\\n"); return 7; }'
    )
    result = subprocess.run(
        [sys.executable, "-m", "cminus", str(source), "-o", str(script), "--run"],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert (result.stdout, result.stderr, result.returncode) == (b"ok\n", b"", 7)
    standalone = subprocess.run(
        [sys.executable, "-I", "-S", str(script)], capture_output=True, timeout=10
    )
    assert (standalone.stdout, standalone.stderr, standalone.returncode) == (
        b"ok\n",
        b"",
        7,
    )


@pytest.mark.parametrize(
    "source",
    ["int main() { @ }", "int main() { return 0 }", "int main() { return missing; }"],
)
def test_phase_errors_preserve_existing_output_and_show_source(
    tmp_path, capsys, source
):
    original = tmp_path / "program.c"
    output = tmp_path / "output.py"
    original.write_text(source)
    output.write_text("existing output")
    assert main([str(original), "-o", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        str(original) in captured.err and source in captured.err and "^" in captured.err
    )
    assert "Traceback" not in captured.err
    assert output.read_text() == "existing output"


def test_io_errors_and_source_overwrite_are_reported(tmp_path, capsys):
    missing = tmp_path / "missing.c"
    assert main([str(missing)]) == 1
    assert capsys.readouterr().err
    source = tmp_path / "program.c"
    source.write_text("int main() {}")
    assert main([str(source), "-o", str(source)]) == 1
    assert "must differ" in capsys.readouterr().err
    assert source.read_text() == "int main() {}"


def test_checker_missing_compiler_returns_two(tmp_path, capsys):
    source = tmp_path / "program.c"
    source.write_text("int main() {}")
    assert checker_main([str(source), "--cc", str(tmp_path / "missing-cc")]) == 2
    assert "cannot run" in capsys.readouterr().err


@pytest.mark.parametrize("status,expected", [(7, 0), (8, 1)])
def test_checker_status_distinguishes_equivalence_from_program_exit(
    tmp_path, capsys, monkeypatch, status, expected
):
    source = tmp_path / "program.c"
    source.write_text("int main() { return 7; }")
    reference = subprocess.CompletedProcess([], 7, stdout=b"", stderr=b"")
    generated = subprocess.CompletedProcess([], status, stdout=b"", stderr=b"")
    monkeypatch.setattr(
        "cminus.extras.gcc_equivalence.compare_files",
        lambda *args, **kwargs: Comparison(reference, generated, "test compiler"),
    )
    assert checker_main([str(source)]) == expected
    captured = capsys.readouterr()
    assert "test compiler" in captured.out
    if expected:
        assert "returncode: C=7; Python=8" in captured.err
    else:
        assert "Equivalent" in captured.out and captured.err == ""


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "abc"])
def test_checker_rejects_invalid_timeouts(value):
    with pytest.raises(SystemExit) as caught:
        checker_main(["program.c", "--timeout", value])
    assert caught.value.code == 2
