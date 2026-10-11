"""Core acceptance: standalone output and exact C11 behavior comparisons."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from cminus.compiler import compile_source
from cminus.errors import CMinusError, SemanticError
from cminus.extras.gcc_equivalence import CheckError, Comparison, compare_files
from cminus.lexer_analyser import tokenize
from cminus.parser import parse

CASES = Path(__file__).parent / "gcc_cases"
COMPILER = os.environ.get("CMINUS_CC", "gcc")
GOLDENS = [
    ("arithmetic.c", b"-2 -1 1 2 715827882\n", 0),
    ("control_flow.c", b"31 99 5\n", 0),
    ("short_circuit.c", b"02:1 1 0 4\n", 0),
    ("functions.c", b"F=120 bool=5\n", 0),
    ("formatting.c", b"%1 -3 ok A\ncount=11|tail", 7),
    ("byte_output.c", b"\xffhiend", 0),
    ("bindings.c", b"20 10 5 9\n1 1\n", 0),
    ("empty.c", b"", 0),
    ("loop_conditions.c", b"0123210123 3\n", 0),
    ("loop_jumps.c", b"while 5 8\nfor 6 11\ndo 5 8\nempty 3\n", 0),
    ("loop_jump_effects.c", b"C0 S0 C1 B1 S1 C2 |C1 D2 C2 C3 |V1 V2 V3 \n", 0),
    ("nested_loop_jumps.c", b"C1 total=648 outer=2\n", 0),
    ("globals.c", b"start 0 0 -2 1\nstate 5 1 11\nshadow 99\nend 4 4 1\n", 0),
    ("global_constants.c", b"-7 6 5 0 1 1 1\n", 0),
    ("prototypes.c", b"1 1 5\n", 0),
    (
        "printf_fields.c",
        b"[+00023][   -7][004   ][   -0009][][     ]\nn=43\n[   -0012][hi    ][caf\xc3][  A][B  ]\n[7    ][7][+][]\n",
        0,
    ),
    (
        "utf8_strings.c",
        "Mabuhay: café ñ 世界\nbytes=25\n[      é][éé    ]\n".encode(),
        0,
    ),
]


@pytest.mark.parametrize("filename,stdout,status", GOLDENS)
def test_standalone_programs(filename, stdout, status, tmp_path):
    result = compile_source((CASES / filename).read_text())
    script = tmp_path / "program.py"
    script.write_text(result.python_source)
    process = subprocess.run(
        [sys.executable, "-I", "-S", str(script)],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert (process.stdout, process.stderr, process.returncode) == (stdout, b"", status)
    assert (
        compile_source((CASES / filename).read_text()).python_source
        == result.python_source
    )


@pytest.mark.skipif(shutil.which(COMPILER) is None, reason="C compiler is unavailable")
@pytest.mark.parametrize("filename,stdout,status", GOLDENS)
def test_exact_c11_equivalence(filename, stdout, status, tmp_path):
    script = tmp_path / "program.py"
    script.write_text(compile_source((CASES / filename).read_text()).python_source)
    comparison = compare_files(CASES / filename, script, compiler=COMPILER)
    assert comparison.equivalent, comparison.differences()
    assert (comparison.c.stdout, comparison.c.stderr, comparison.c.returncode) == (
        stdout,
        b"",
        status,
    )


@pytest.mark.parametrize(
    "source",
    [
        "int main() { int **p; }",
        "int main() { int a[3]; }",
        "int main() { float f = 1.5; }",
        "int main() { string s; }",
        "int main() { int i=0; i++; }",
        "int main() { if (1) int x=0; }",
        "#define X 1\nint main() {}",
        "#include <stdlib.h>\nint main() {}",
        "#include <stdio.h> int main() {}",
        'int main() { printf("%f", 1); }',
        "int main() { return 0x10; }",
        "int main() { return 012; }",
    ],
)
def test_deferred_and_excluded_features_are_diagnosed(source):
    with pytest.raises(CMinusError) as caught:
        compile_source(source)
    assert caught.value.line >= 1 and caught.value.column >= 1


def test_forward_call_is_rejected_at_the_call():
    with pytest.raises(SemanticError, match="must be declared before") as caught:
        compile_source("int main() { return helper(); }\nint helper() { return 1; }")
    assert (caught.value.line, caught.value.column) == (1, 21)


def test_comments_escapes_and_crlf_preserve_positions():
    source = '/* first\r\nsecond */\r\nint main(void) { // comment\r\n    printf("a\\"b\\n\\t\\\\");\r\n}\r\n'
    tokens = tokenize(source)
    call = next(token for token in tokens if token.lexeme == "printf")
    assert (call.line, call.column) == (4, 5)
    literal = parse(tokens).functions[0].body.statements[0].expr.args[0]
    assert literal.value == 'a"b\n\t\\'


@pytest.mark.parametrize(
    "source,line,column",
    [
        ("/* unfinished", 1, 1),
        ('"unfinished', 1, 1),
        ('"bad\\q"', 1, 5),
        ('"bad\n"', 1, 1),
    ],
)
def test_lexical_failure_locations(source, line, column):
    with pytest.raises(CMinusError) as caught:
        tokenize(source)
    assert (caught.value.line, caught.value.column) == (line, column)


@pytest.mark.parametrize(
    "field,value", [("stdout", b"text\n"), ("stderr", b"error"), ("returncode", 7)]
)
def test_comparison_detects_each_observable_difference(field, value):
    c = subprocess.CompletedProcess([], 0, stdout=b"text", stderr=b"")
    python = subprocess.CompletedProcess([], 0, stdout=b"text", stderr=b"")
    setattr(python, field, value)
    result = Comparison(c, python, "test compiler")
    assert not result.equivalent
    assert result.differences()[0].startswith(field + ":")


def test_missing_compiler_is_a_tool_failure(tmp_path):
    with pytest.raises(CheckError, match="cannot run"):
        compare_files(
            CASES / "empty.c",
            tmp_path / "program.py",
            compiler=str(tmp_path / "missing-cc"),
        )


@pytest.mark.skipif(shutil.which(COMPILER) is None, reason="C compiler is unavailable")
def test_compilation_failure_is_reported(tmp_path):
    invalid = tmp_path / "invalid.c"
    invalid.write_text("this is not C;")
    with pytest.raises(CheckError, match="C compilation failed"):
        compare_files(invalid, tmp_path / "program.py", compiler=COMPILER)


@pytest.mark.parametrize(
    "stage", [1, 2, 3, 4], ids=["identity", "compile", "native", "python"]
)
def test_timeouts_apply_to_each_subprocess(monkeypatch, stage):
    calls = []

    def timeout(command, **kwargs):
        calls.append(kwargs["timeout"])
        if len(calls) == stage:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(
            command, 0, stdout=b"test compiler\n", stderr=b""
        )

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(CheckError, match="timed out after 2s"):
        compare_files(CASES / "empty.c", "unused.py", timeout=2)
    assert calls == [2] * stage


@pytest.mark.skipif(shutil.which(COMPILER) is None, reason="C compiler is unavailable")
def test_generated_program_timeout_is_reported(tmp_path):
    script = tmp_path / "hanging.py"
    script.write_text("while True: pass\n")
    with pytest.raises(CheckError, match="timed out"):
        compare_files(CASES / "empty.c", script, compiler=COMPILER, timeout=1)
