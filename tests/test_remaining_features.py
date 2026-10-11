"""Global state, function declarations, and the required formatting pass."""

import ast
import json
from pathlib import Path
import subprocess
import sys

import pycodestyle
import pytest

from cminus.ast_nodes import FunctionDecl, FunctionPrototype, VarDecl
from cminus.code_generator import generate
from cminus.compiler import compile_source
from cminus.errors import ParseError, SemanticError
from cminus.extras.formatter import FormattingError, format_source
from cminus.lexer_analyser import tokenize
from cminus.main import main
from cminus.parser import parse
from cminus.semantic_analyser import analyse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT / "tests/gcc_cases").glob("*.c")) + sorted(
    (ROOT / "examples").glob("*.c")
)


def test_top_level_ast_preserves_order_and_separates_definitions():
    tree = parse(
        tokenize(
            "int total; int add(int, bool ready); int main(void) {} int add(int n, bool b) { return n; }"
        )
    )
    assert [type(node) for node in tree.declarations] == [
        VarDecl,
        FunctionPrototype,
        FunctionDecl,
        FunctionDecl,
    ]
    assert [node.name for node in tree.globals] == ["total"]
    assert [node.name for node in tree.functions] == ["main", "add"]
    prototype = tree.declarations[1]
    assert [(param.type_name, param.name) for param in prototype.params] == [
        ("int", ""),
        ("bool", "ready"),
    ]


@pytest.mark.parametrize(
    "source,message",
    [
        ("int x = x; int main() {}", "read in its own initializer"),
        ("int x; int y = x; int main() {}", "integer constant expression"),
        (
            "int f() { return 1; } int x = f(); int main() {}",
            "integer constant expression",
        ),
        ("int x; int y = (x = 1); int main() {}", "integer constant expression"),
        ("int x = 1 / 0; int main() {}", "division by zero"),
        ("int x = 1 % 0; int main() {}", "division by zero"),
        ('int x = "text"; int main() {}', "cannot assign 'string'"),
        ("void x; int main() {}", "cannot have type 'void'"),
        ("int x; bool x; int main() {}", "redeclaration of 'x'"),
        ("int x; int x() { return 0; } int main() {}", "redeclaration of 'x'"),
        ("int x() { return 0; } int x; int main() {}", "redeclaration of 'x'"),
        ("int main() { return later; } int later;", "used before it is declared"),
        ("int f(int); bool f(int); int main() {}", "conflicting declaration"),
        ("int f(int); int f(bool); int main() {}", "conflicting declaration"),
        ("int f(int); int f(int, int); int main() {}", "conflicting declaration"),
        (
            "int f(int); bool f(int n) { return n; } int main() {}",
            "conflicting declaration",
        ),
        ("int f(int); int main() { return f(1); }", "declared but not defined"),
        ("int main(void);", "'main' function is not defined"),
        ("int f(int a, int a); int main() {}", "redeclaration of 'a'"),
        ("int printf(int); int main() {}", "duplicate function 'printf'"),
        ('int main() { printf("%*d", "bad", 1); }', "field width expects int or bool"),
        (
            'int main() { printf("%.*s", "bad", "ok"); }',
            "precision expects int or bool",
        ),
        ('int main() { printf("%*.*d", 1, 2); }', "expects 3 arguments"),
        ('int main() { printf("%*.*d", 1, 2, "bad"); }', "expects int or bool"),
        ('int main() { printf("%05s", "ok"); }', "invalid printf flags"),
        ('int main() { printf("%.2c", 65); }', "precision is invalid"),
        ('int main() { printf("%5%", 1); }', "unsupported printf format"),
    ],
)
def test_invalid_globals_and_prototypes_are_positioned(source, message):
    with pytest.raises(SemanticError, match=message) as caught:
        compile_source(source)
    assert caught.value.line >= 1 and caught.value.column >= 1


def test_unnamed_parameters_are_allowed_only_in_prototypes():
    with pytest.raises(ParseError, match="require parameter names") as caught:
        parse(tokenize("int f(int) { return 1; } int main() {}"))
    assert (caught.value.line, caught.value.column) == (1, 7)


def test_global_types_and_constant_values_are_visible_in_symbols():
    result = compile_source(
        "int n; bool b = -2; int q = -7 / 3; int f(int); int f(int x) { return x; } int main() { return f(n); }"
    )
    globals = result.symbols.global_scope.symbols
    assert [
        (globals[name].is_global, globals[name].initial_value)
        for name in ("n", "b", "q")
    ] == [(True, 0), (True, True), (True, -2)]
    prototype, definition = result.program.declarations[3:5]
    assert prototype.binding_id == definition.binding_id
    assert globals["f"].defined
    assert "var n: int" in result.symbols.dump()


def test_unused_prototype_needs_no_runtime_definition():
    result = compile_source("void unused(int); int main() { return 0; }")
    assert "unused" not in result.python_source


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.name)
def test_all_generated_programs_are_pep8_and_formatting_preserves_the_ast(
    source, tmp_path
):
    result = compile_source(source.read_text())
    raw = generate(result.program, result.symbols)
    assert ast.dump(ast.parse(raw)) == ast.dump(ast.parse(result.python_source))
    assert format_source(result.python_source) == result.python_source
    script = tmp_path / "formatted.py"
    script.write_text(result.python_source)
    checker = pycodestyle.Checker(filename=str(script), quiet=True, max_line_length=79)
    assert checker.check_all() == 0


def test_long_escaped_literal_keeps_exact_bytes_and_obeys_line_length(tmp_path):
    value = 'a "quoted" \\ path\n' * 15
    result = compile_source(
        f'#include <stdio.h>\nint main() {{ printf("%s", {json.dumps(value)}); }}'
    )
    script = tmp_path / "long_string.py"
    script.write_text(result.python_source)
    assert (
        pycodestyle.Checker(
            filename=str(script), quiet=True, max_line_length=79
        ).check_all()
        == 0
    )
    process = subprocess.run(
        [sys.executable, "-I", "-S", str(script)], capture_output=True, timeout=10
    )
    assert (process.stdout, process.stderr, process.returncode) == (
        value.encode(),
        b"",
        0,
    )


def test_many_long_global_names_keep_unique_bindings_and_formatted_declarations(
    tmp_path,
):
    names = ["a_very_long_common_identifier_prefix_" + str(index) for index in range(5)]
    declarations = "".join(f"int {name} = {index};" for index, name in enumerate(names))
    assignments = "".join(f"{name} = {name} + 1;" for name in names)
    total = " + ".join(names)
    result = compile_source(
        declarations + f"int main() {{ {assignments} return {total}; }}"
    )
    script = tmp_path / "long_names.py"
    script.write_text(result.python_source)
    assert (
        pycodestyle.Checker(
            filename=str(script), quiet=True, max_line_length=79
        ).check_all()
        == 0
    )
    process = subprocess.run(
        [sys.executable, "-I", "-S", str(script)], capture_output=True, timeout=10
    )
    assert (process.stdout, process.stderr, process.returncode) == (b"", b"", 15)


def test_formatter_rejects_syntax_errors_and_semantic_changes(monkeypatch):
    with pytest.raises(FormattingError, match="cannot format"):
        format_source("invalid Python!")
    monkeypatch.setattr(
        "black.format_file_contents", lambda *args, **kwargs: "value = 2\n"
    )
    with pytest.raises(FormattingError, match="changed"):
        format_source("value = 1\n")


def test_formatter_error_preserves_cli_output_and_is_reported(
    tmp_path, capsys, monkeypatch
):
    source = tmp_path / "program.c"
    output = tmp_path / "program.py"
    source.write_text("int main() { return 0; }")
    output.write_text("existing")

    def fail(source):
        raise FormattingError("formatter test failure")

    monkeypatch.setattr("cminus.compiler.format_source", fail)
    assert main([str(source), "-o", str(output)]) == 1
    assert "formatting error: formatter test failure" in capsys.readouterr().err
    assert output.read_text() == "existing"
