"""Pending integration tests for every committed C example."""

import subprocess
import sys
from pathlib import Path

import pytest

from cminus.code_generator import generate
from cminus.errors import SemanticError
from cminus.lexer_analyser import tokenize
from cminus.parser import parse
from cminus.semantic_analyser import analyse

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
pytestmark = pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="example pipelines depend on unfinished compiler stages",
)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("hello.c", "Hello, C-Minus!\n"),
        ("factorial.c", "1! = 1\n2! = 2\n3! = 6\n4! = 24\n5! = 120\n"),
    ],
)
def test_valid_examples_compile_and_run(
    filename: str,
    expected: str,
    tmp_path: Path,
) -> None:
    source = (EXAMPLES / filename).read_text(encoding="utf-8")
    tree = parse(tokenize(source))
    generated = generate(tree, analyse(tree))
    compile(generated, filename + ".py", "exec")
    script = tmp_path / (filename + ".py")
    script.write_text(generated, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected
    assert result.stderr == ""


@pytest.mark.parametrize(
    "filename,message,line,column",
    [
        (
            "type_mismatch.c",
            "cannot assign 'string' to variable 'a' of type 'int'",
            2,
            13,
        ),
        (
            "undeclared_variable.c",
            "variable 'count' is used before it is declared",
            3,
            16,
        ),
        (
            "wrong_arg_count.c",
            "function 'add' expects 2 arguments but 3 were given",
            6,
            12,
        ),
    ],
)
def test_error_examples_report_semantic_diagnostics_at_the_source_location(
    filename: str,
    message: str,
    line: int,
    column: int,
) -> None:
    source = (EXAMPLES / "errors" / filename).read_text(encoding="utf-8")
    with pytest.raises(SemanticError) as caught:
        analyse(parse(tokenize(source)))
    assert caught.value.message == message
    assert (caught.value.line, caught.value.column) == (line, column)
