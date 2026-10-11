"""Jump parsing, loop-context diagnostics, and nested C execution equivalence."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from cminus.ast_nodes import Break, Continue
from cminus.compiler import compile_source
from cminus.errors import ParseError, SemanticError
from cminus.extras.gcc_equivalence import compare_files
from cminus.lexer_analyser import tokenize
from cminus.parser import parse
from cminus.semantic_analyser import SemanticAnalyser

COMPILER = os.environ.get("CMINUS_CC", "gcc")


def test_jump_nodes_preserve_locations_in_braced_and_unbraced_bodies():
    tree = parse(
        tokenize(
            "int main() {\n"
            "    while (1) break;\n"
            "    do continue; while (0);\n"
            "    for (;;) { break; continue; }\n"
            "}"
        )
    )
    while_loop, do_loop, for_loop = tree.functions[0].body.statements
    assert isinstance(while_loop.body, Break)
    assert (while_loop.body.line, while_loop.body.column) == (2, 15)
    assert isinstance(do_loop.body, Continue)
    assert (do_loop.body.line, do_loop.body.column) == (3, 8)
    assert isinstance(for_loop.body.statements[0], Break)
    assert isinstance(for_loop.body.statements[1], Continue)


@pytest.mark.parametrize("keyword", ["break", "continue"])
@pytest.mark.parametrize("suffix", ["", " 1", "()"])
def test_jumps_require_a_semicolon_and_take_no_expression(keyword, suffix):
    with pytest.raises(ParseError, match="expected ';'"):
        parse(tokenize(f"int main() {{ while (1) {{ {keyword}{suffix} }} }}"))


@pytest.mark.parametrize("keyword", ["break", "continue"])
@pytest.mark.parametrize("prefix", ["", "if (0) ", "while (1) { break; } "])
def test_jump_outside_loop_is_a_positioned_semantic_error(keyword, prefix):
    source = f"int main() {{\n    {prefix}{keyword};\n}}"
    with pytest.raises(
        SemanticError, match=f"{keyword} statement outside a loop"
    ) as caught:
        compile_source(source)
    assert (caught.value.line, caught.value.column) == (2, 5 + len(prefix))


@pytest.mark.parametrize("keyword", ["break", "continue"])
def test_calling_a_helper_from_a_loop_does_not_legalize_its_jump(keyword):
    source = (
        f"void helper() {{\n    {keyword};\n}}\n"
        "int main() { while (1) { helper(); break; } }"
    )
    with pytest.raises(
        SemanticError, match=f"{keyword} statement outside a loop"
    ) as caught:
        compile_source(source)
    assert (caught.value.line, caught.value.column) == (2, 5)


def test_semantic_loop_context_resets_after_success_and_nested_failure():
    analyser = SemanticAnalyser()
    analyser.analyse(parse(tokenize("int main() { while (1) { break; } }")))
    with pytest.raises(SemanticError, match="missing"):
        analyser.analyse(
            parse(
                tokenize(
                    "int main() { for (;;) { do { return missing; } while (1); } }"
                )
            )
        )
    with pytest.raises(SemanticError, match="continue statement outside a loop"):
        analyser.analyse(parse(tokenize("int main() { continue; }")))
    analyser.analyse(parse(tokenize("int main() { do { continue; } while (0); }")))


@pytest.mark.parametrize("keyword", ["break", "continue"])
def test_cli_reports_invalid_jump_and_preserves_existing_output(tmp_path, keyword):
    source = tmp_path / "invalid.c"
    output = tmp_path / "existing.py"
    source.write_text(f"int main() {{\n    {keyword};\n}}")
    output.write_text("existing output")
    process = subprocess.run(
        [sys.executable, "-m", "cminus", str(source), "-o", str(output)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert process.returncode == 1
    assert process.stdout == ""
    assert f":2:5: semantic error: {keyword} statement outside a loop" in process.stderr
    assert "^" in process.stderr and "Traceback" not in process.stderr
    assert output.read_text() == "existing output"


def loop_source(kind, name, limit, body):
    condition = f'printf("{name[0]}?") && {name} < {limit}'
    if kind == "while":
        return f"while ({condition}) {{ {body} }}"
    if kind == "do":
        return f"do {{ {body} }} while ({condition});"
    return f'for (; {condition}; printf("{name[0]}+")) {{ {body} }}'


@pytest.mark.skipif(shutil.which(COMPILER) is None, reason="C compiler is unavailable")
@pytest.mark.parametrize("outer_kind", ["while", "do", "for"])
@pytest.mark.parametrize("inner_kind", ["while", "do", "for"])
def test_nested_jumps_target_the_nearest_loop(outer_kind, inner_kind, tmp_path):
    inner = loop_source(
        inner_kind,
        "inner",
        4,
        """
        inner = inner + 1;
        if (inner == 2) continue;
        if (inner == 4) break;
        total = total + outer * 10 + inner;
    """,
    )
    outer = loop_source(
        outer_kind,
        "outer",
        3,
        f"""
        outer = outer + 1;
        inner = 0;
        {inner}
        if (outer == 1) continue;
        if (outer == 2) break;
        total = total + 1000;
    """,
    )
    source = f"""#include <stdio.h>
int main(void) {{
    int outer = 0;
    int inner = 0;
    int total = 0;
    {outer}
    printf(" result=%d,%d,%d\\n", outer, inner, total);
    return 0;
}}
"""
    original = tmp_path / "nested.c"
    script = tmp_path / "nested.py"
    original.write_text(source)
    script.write_text(compile_source(source).python_source)
    result = compare_files(original, script, compiler=COMPILER)
    assert result.equivalent, result.differences()
    assert result.python.stdout.endswith(b" result=2,4,68\n")
    assert result.python.stderr == b"" and result.python.returncode == 0
