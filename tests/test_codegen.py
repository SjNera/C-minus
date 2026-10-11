"""checks that supported ASTs produce executable Python."""

import subprocess
import sys
from pathlib import Path

import pytest

from cminus.ast_nodes import (
    Assign,
    BinaryOp,
    Block,
    BoolLiteral,
    Call,
    DoWhile,
    ExprStmt,
    For,
    FunctionDecl,
    Identifier,
    If,
    IntLiteral,
    Param,
    Program,
    Return,
    UnaryOp,
    VarDecl,
    While,
)
from cminus.code_generator import generate
from cminus.semantic_analyser import analyse


def run_generated_program(
    tree: Program, tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    source = generate(tree, analyse(tree))
    assert isinstance(source, str) and source.strip()
    compile(source, "generated.py", "exec")
    script = tmp_path / "generated.py"
    script.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_minimal_main_generates_executable_python(tmp_path: Path) -> None:
    tree = Program([FunctionDecl("int", "main", [], Block([Return(IntLiteral(0))]))])
    result = run_generated_program(tree, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


def test_nested_loops_assignments_and_boolean_conditions_compile(
    tmp_path: Path,
) -> None:
    tree = Program(
        [
            FunctionDecl(
                "int",
                "main",
                [],
                Block(
                    [
                        VarDecl("int", "count", IntLiteral(0)),
                        VarDecl("bool", "ready", BoolLiteral(True)),
                        For(
                            VarDecl("int", "i", IntLiteral(0)),
                            BinaryOp("<", Identifier("i"), IntLiteral(2)),
                            Assign(
                                Identifier("i"),
                                BinaryOp("+", Identifier("i"), IntLiteral(1)),
                            ),
                            Block(
                                [
                                    ExprStmt(
                                        Assign(
                                            Identifier("count"),
                                            BinaryOp(
                                                "+", Identifier("count"), IntLiteral(1)
                                            ),
                                        )
                                    )
                                ]
                            ),
                        ),
                        While(
                            BinaryOp("<", Identifier("count"), IntLiteral(3)),
                            ExprStmt(
                                Assign(
                                    Identifier("count"),
                                    BinaryOp("+", Identifier("count"), IntLiteral(1)),
                                )
                            ),
                        ),
                        DoWhile(
                            ExprStmt(
                                Assign(
                                    Identifier("count"),
                                    BinaryOp("-", Identifier("count"), IntLiteral(1)),
                                )
                            ),
                            BoolLiteral(False),
                        ),
                        If(UnaryOp("!", Identifier("ready")), Block()),
                        Return(IntLiteral(0)),
                    ]
                ),
            )
        ]
    )
    result = run_generated_program(tree, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


def test_helper_calls_and_recursion_compile(tmp_path: Path) -> None:
    factorial = FunctionDecl(
        "int",
        "factorial",
        [Param("int", "n")],
        Block(
            [
                If(
                    BinaryOp("<=", Identifier("n"), IntLiteral(1)),
                    Return(IntLiteral(1)),
                ),
                Return(
                    BinaryOp(
                        "*",
                        Identifier("n"),
                        Call(
                            "factorial", [BinaryOp("-", Identifier("n"), IntLiteral(1))]
                        ),
                    )
                ),
            ]
        ),
    )
    main = FunctionDecl(
        "int",
        "main",
        [],
        Block(
            [
                ExprStmt(Call("factorial", [IntLiteral(5)])),
                Return(IntLiteral(0)),
            ]
        ),
    )
    result = run_generated_program(Program([factorial, main]), tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
