"""parser contracts using C constructs already represented by the AST."""

import pytest

from cminus.ast_nodes import (
    Assign,
    BinaryOp,
    Call,
    ExprStmt,
    For,
    IntLiteral,
    Program,
    Return,
)
from cminus.errors import ParseError
from cminus.lexer_analyser import tokenize
from cminus.parser import parse


def test_minimal_main_builds_a_program_and_return_statement() -> None:
    tree = parse(tokenize("int main() { return 0; }"))
    assert isinstance(tree, Program)
    assert len(tree.functions) == 1
    main = tree.functions[0]
    assert (main.return_type, main.name, main.params) == ("int", "main", [])
    assert len(main.body.statements) == 1
    statement = main.body.statements[0]
    assert isinstance(statement, Return)
    assert isinstance(statement.value, IntLiteral)
    assert statement.value.value == 0
    assert statement.value.resolved_type is None


def test_multiplication_binds_more_tightly_than_addition() -> None:
    tree = parse(tokenize("int main() { return 1 + 2 * 3; }"))
    statement = tree.functions[0].body.statements[0]
    assert isinstance(statement, Return)
    expression = statement.value
    assert isinstance(expression, BinaryOp) and expression.op == "+"
    assert isinstance(expression.left, IntLiteral) and expression.left.value == 1
    assert isinstance(expression.right, BinaryOp) and expression.right.op == "*"
    assert (
        isinstance(expression.right.left, IntLiteral)
        and expression.right.left.value == 2
    )
    assert (
        isinstance(expression.right.right, IntLiteral)
        and expression.right.right.value == 3
    )


def test_assignment_is_right_associative() -> None:
    tree = parse(tokenize("int main() { int a; int b; a = b = 3; return a; }"))
    statement = tree.functions[0].body.statements[2]
    assert isinstance(statement, ExprStmt)
    expression = statement.expr
    assert isinstance(expression, Assign) and expression.target.name == "a"
    assert isinstance(expression.value, Assign) and expression.value.target.name == "b"
    assert isinstance(expression.value.value, IntLiteral)
    assert expression.value.value.value == 3


def test_function_parameters_and_call_arguments_preserve_order() -> None:
    tree = parse(
        tokenize(
            "int add(int a, int b) { return a + b; } "
            "int main() { return add(1, 2); }"
        )
    )
    helper, main = tree.functions
    assert [(param.type_name, param.name) for param in helper.params] == [
        ("int", "a"),
        ("int", "b"),
    ]
    statement = main.body.statements[0]
    assert isinstance(statement, Return)
    assert isinstance(statement.value, Call) and statement.value.callee == "add"
    assert all(isinstance(argument, IntLiteral) for argument in statement.value.args)
    assert [argument.value for argument in statement.value.args] == [1, 2]


def test_for_loop_allows_an_empty_header() -> None:
    tree = parse(tokenize("int main() { for (;;) { return 0; } }"))
    loop = tree.functions[0].body.statements[0]
    assert isinstance(loop, For)
    assert (loop.init, loop.condition, loop.step) == (None, None, None)


@pytest.mark.parametrize(
    "source",
    [
        "int main() { return 0 }",
        "int main() { return 0;",
        "int main( { return 0; }",
    ],
)
def test_malformed_programs_raise_syntax_errors(source: str) -> None:
    with pytest.raises(ParseError):
        parse(tokenize(source))
