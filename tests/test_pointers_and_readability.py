"""Pointer aliasing and the readability of standalone generated Python."""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pycodestyle
import pytest

from cminus.compiler import compile_source
from cminus.errors import CMinusError, SemanticError
from cminus.extras.gcc_equivalence import compare_files
from cminus.lexer_analyser import tokenize
from cminus.parser import parse

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get("CMINUS_CC", "gcc")
GOLDENS = [
    (
        "pointer_aliases.c",
        b"shared 11 11\nrebound 12 12 12\nidentity 1 1 1\nnull 1 0 1 1 1\nunchanged 12 12\n",
    ),
    ("pointer_functions.c", b"values 7 15 7\ncopy 7 99\nbool 0\nalias 7\n"),
    ("pointer_globals.c", b"start 0 0 1\nend 6 1 22 1\n"),
    (
        "pointer_loops.c",
        b"for 4 4\nloops 8\nshadow 40 8\n10 11 12 \nouter 8\n",
    ),
    ("pointer_initialization.c", b"9 15 4\n"),
]


def execute(source, tmp_path):
    compiled = compile_source(source)
    script = tmp_path / "program.py"
    script.write_text(compiled.python_source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(script)],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert not result.stderr, result.stderr
    assert (
        pycodestyle.Checker(
            filename=str(script), quiet=True, max_line_length=79
        ).check_all()
        == 0
    )
    return compiled, script, result


@pytest.mark.parametrize("filename,expected", GOLDENS)
def test_pointer_programs_execute_standalone(filename, expected, tmp_path):
    compiled, _, result = execute(
        (ROOT / "tests/gcc_cases" / filename).read_text(), tmp_path
    )
    assert (result.stdout, result.returncode) == (expected, 0)
    assert "__cm" not in compiled.python_source


@pytest.mark.skipif(
    shutil.which(COMPILER) is None, reason="C compiler unavailable"
)
@pytest.mark.parametrize("filename,expected", GOLDENS)
def test_pointer_programs_match_c11(filename, expected, tmp_path):
    source = ROOT / "tests/gcc_cases" / filename
    _, script, _ = execute(source.read_text(), tmp_path)
    comparison = compare_files(source, script, compiler=COMPILER)
    assert comparison.equivalent, comparison.differences()
    assert comparison.c.stdout == expected


@pytest.mark.parametrize(
    "source,message",
    [
        ("int main() { int **p; }", "multiple pointer levels"),
        ("int main() { void *p; }", "outside the core"),
        ("void *p; int main() {}", "void pointers"),
        ("int *f() { return 0; } int main() {}", "invalid return type"),
        ("int main() { int *p = 1; }", "cannot assign 'int'"),
        ("int main() { bool x; int *p = &x; }", "cannot assign 'bool\\*'"),
        ("int main() { int x; bool *p = &x; }", "cannot assign 'int\\*'"),
        ("int main() { int *p; int n = p; }", "cannot assign 'int\\*'"),
        ("int main() { int x; *x = 2; }", "dereference requires"),
        ("int main() { int *p; p = &p; }", "pointer-to-pointer"),
        ("int main() { int *p = &1; }", "address-of requires"),
        ("int main() { int x; int *p = &(x + 1); }", "address-of requires"),
        (
            "int f() { return 0; } int main() { int *p = &f(); }",
            "address-of requires",
        ),
        ("int main() { int *p; return p + 1; }", "cannot be applied"),
        ("int main() { int *p; return p * 1; }", "cannot be applied"),
        ("int main() { int *p; int *q; return p - q; }", "cannot be applied"),
        ("int main() { int *p; int *q; return p < q; }", "cannot be applied"),
        (
            "int main() { int *p; bool *q; return p == q; }",
            "cannot be applied",
        ),
        ("int main() { int *p; return p == 1; }", "cannot be applied"),
        ('int main() { int *p; printf("%d", p); }', "expects int or bool"),
        (
            'int main() { int *p; printf("%p", p); }',
            "unsupported printf format",
        ),
        (
            "void f(int *p) {} int main() { bool b; f(&b); }",
            "expects type 'int\\*'",
        ),
        ("void f(int *p) {} int main() { f(1); }", "expects type 'int\\*'"),
        (
            "void f(int *); void f(bool *); int main() {}",
            "conflicting declaration",
        ),
        (
            "int x; int *p = &x; int *q = p; int main() {}",
            "global pointer initializer",
        ),
        (
            "int *p = &later; int later; int main() {}",
            "used before it is declared",
        ),
    ],
)
def test_unsupported_or_mismatched_pointer_operations_have_positions(
    source, message
):
    with pytest.raises(CMinusError, match=message) as caught:
        compile_source(source)
    assert caught.value.line > 0 and caught.value.column > 0


def test_pointer_ast_and_symbols_share_declaration_bindings():
    parsed = parse(
        tokenize(
            "void f(int *); void f(int *p) { *p = 8; } int main() { int n=1; int *p=&n; f(p); }"
        )
    )
    result = compile_source(
        "void f(int *); void f(int *p) { *p = 8; } int main() { int n=1; int *p=&n; f(p); }"
    )
    assert parsed.declarations[0].params[0].type_name == "int*"
    main_scope = next(
        scope for scope in result.symbols.all_scopes if scope.name == "main"
    )
    assert main_scope.symbols["n"].address_taken
    assert not main_scope.symbols["p"].address_taken
    assert main_scope.symbols["p"].type_name == "int*"
    assignment = result.program.functions[0].body.statements[0].expr
    assert (
        assignment.target.op == "*"
        and assignment.target.resolved_type == "int"
    )


def test_literal_zero_can_be_passed_without_dereferencing(tmp_path):
    _, _, result = execute(
        "int empty(int *p) { return p == 0; } int main() { return empty(0); }",
        tmp_path,
    )
    assert result.returncode == 1


def test_plain_programs_keep_names_and_omit_unneeded_helpers():
    output = compile_source(
        "int main() { int x=5; return x+2; }"
    ).python_source
    assert "x = 5" in output and "return x + 2" in output
    assert (
        "import " not in output
        and "int(" not in output
        and "__cm" not in output
    )
    assert output.count("return ") == 1
    assert len(output.splitlines()) < 12


def test_hello_is_a_short_print_program():
    output = compile_source(
        (ROOT / "examples/hello.c").read_text()
    ).python_source
    assert 'print("Hello, C-Minus!", flush=True)' in output
    assert "parse_printf_format" not in output and "def printf" not in output
    assert len(output.splitlines()) <= 16


def test_common_formats_use_f_strings_with_c_integer_and_boolean_values(
    tmp_path,
):
    compiled, _, result = execute(
        '#include <stdbool.h>\nint main() { int n=-7; bool b=true; printf("[%05d][%-5d][%+d][%d]\\n", n, n, n, b); }',
        tmp_path,
    )
    assert result.stdout == b"[-0007][-7   ][-7][1]\n"
    assert (
        'print(f"' in compiled.python_source
        and "def printf" not in compiled.python_source
    )


def test_same_parameter_names_stay_readable_in_separate_functions():
    output = compile_source(
        "int first(int n) { return n; } int second(int n) { return n; } int main() { return second(first(1)); }"
    ).python_source
    assert "def first(n):" in output and "def second(n):" in output


def test_shadowing_and_python_helper_collisions_keep_behavior(tmp_path):
    _, _, result = execute(
        'int Reference=1; int sys=2; int print=3; int format=4; int class=5; int main() { int x=6; printf("%d ",x); { int x=7; printf("%d ",x); } printf("%d %d %d %d %d %d\\n",x,Reference,sys,print,format,class); }',
        tmp_path,
    )
    assert result.stdout == b"6 7 6 1 2 3 4 5\n"


def test_nested_printf_returns_utf8_byte_count_and_evaluates_once(tmp_path):
    compiled, _, result = execute(
        'int count; int once() { count=count+1; return 7; } int main() { int size=printf("é%d",once()); printf(" bytes=%d calls=%d\\n",size,count); }',
        tmp_path,
    )
    assert result.stdout == "é7 bytes=3 calls=1\n".encode()
    assert (
        "def write(text):" in compiled.python_source
        and "parse_printf_format" not in compiled.python_source
    )


def test_long_formatted_output_wraps_without_changing_text(tmp_path):
    text = "a long literal " * 12
    _, _, result = execute(
        f'int main() {{ int long_variable_name=9; printf("{text}%d\\n",long_variable_name); }}',
        tmp_path,
    )
    assert result.stdout == (text + "9\n").encode()


def test_text_output_stays_utf8_with_a_different_python_io_encoding(tmp_path):
    compiled, script, _ = execute(
        'int main() { printf("café\\n"); }', tmp_path
    )
    environment = dict(os.environ, PYTHONIOENCODING="latin-1")
    result = subprocess.run(
        [sys.executable, str(script)],
        env=environment,
        capture_output=True,
        timeout=10,
    )
    assert (result.stdout, result.stderr, result.returncode) == (
        "café\n".encode(),
        b"",
        0,
    )
