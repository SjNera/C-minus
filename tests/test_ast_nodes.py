"""Contracts shared by the parser, semantic analyser, and code generator."""

from collections.abc import Callable

import pytest

from cminus.ast_nodes import (
    Assign,
    BinaryOp,
    Block,
    BoolLiteral,
    Call,
    DoWhile,
    Expr,
    ExprStmt,
    For,
    FunctionDecl,
    Identifier,
    If,
    IntLiteral,
    Node,
    Param,
    Program,
    Return,
    StringLiteral,
    UnaryOp,
    VarDecl,
    While,
)


@pytest.mark.parametrize(
    "make_node",
    [
        pytest.param(lambda **kw: IntLiteral(42, **kw), id="int"),
        pytest.param(lambda **kw: BoolLiteral(False, **kw), id="bool"),
        pytest.param(lambda **kw: StringLiteral("hello\n", **kw), id="string"),
        pytest.param(lambda **kw: Identifier("x", **kw), id="identifier"),
        pytest.param(
            lambda **kw: Assign(Identifier("x"), IntLiteral(1), **kw), id="assign"
        ),
        pytest.param(
            lambda **kw: BinaryOp("+", IntLiteral(1), IntLiteral(2), **kw),
            id="binary",
        ),
        pytest.param(lambda **kw: UnaryOp("!", BoolLiteral(True), **kw), id="unary"),
        pytest.param(lambda **kw: Call("helper", **kw), id="call"),
        pytest.param(lambda **kw: VarDecl("int", "x", **kw), id="declaration"),
        pytest.param(lambda **kw: ExprStmt(IntLiteral(1), **kw), id="expression-stmt"),
        pytest.param(lambda **kw: Block(**kw), id="block"),
        pytest.param(lambda **kw: If(BoolLiteral(True), Block(), **kw), id="if"),
        pytest.param(lambda **kw: While(BoolLiteral(True), Block(), **kw), id="while"),
        pytest.param(lambda **kw: DoWhile(Block(), BoolLiteral(False), **kw), id="do"),
        pytest.param(lambda **kw: For(None, None, None, Block(), **kw), id="for"),
        pytest.param(lambda **kw: Return(**kw), id="return"),
        pytest.param(lambda **kw: Param("int", "n", **kw), id="parameter"),
        pytest.param(
            lambda **kw: FunctionDecl("int", "main", [], Block(), **kw),
            id="function",
        ),
        pytest.param(lambda **kw: Program([], **kw), id="program"),
    ],
)
def test_source_locations_do_not_displace_node_payloads(
    make_node: Callable[..., Node],
) -> None:
    default = make_node()
    located = make_node(line=7, column=12)
    assert (default.line, default.column) == (0, 0)
    assert (located.line, located.column) == (7, 12)
    if isinstance(located, Expr):
        assert located.resolved_type is None


def test_expression_annotations_and_locations_are_independent() -> None:
    left = IntLiteral(1, line=3, column=5, resolved_type="int")
    right = IntLiteral(2, line=3, column=9)
    expression = BinaryOp("+", left, right, line=3, column=7)
    expression.resolved_type = "int"

    assert expression.left is left and expression.right is right
    assert left.resolved_type == "int"
    assert right.resolved_type is None
    assert (left.line, left.column) == (3, 5)
    assert (expression.line, expression.column) == (3, 7)
    assert (right.line, right.column) == (3, 9)


def test_default_collections_do_not_leak_between_programs() -> None:
    first_call, second_call = Call("printf"), Call("printf")
    first_block, second_block = Block(), Block()
    first_program, second_program = Program([]), Program([])

    first_call.args.append(StringLiteral("hello\n"))
    first_block.statements.append(ExprStmt(first_call))
    first_program.includes.append("stdio.h")

    assert second_call.args == []
    assert second_block.statements == []
    assert second_program.includes == []


def test_optional_nodes_can_represent_empty_c_constructs() -> None:
    declaration = VarDecl("int", "x")
    branch = If(BoolLiteral(True), Return())
    loop = For(None, None, None, Block())

    assert declaration.init is None
    assert branch.else_branch is None
    assert isinstance(branch.then_branch, Return)
    assert branch.then_branch.value is None
    assert (loop.init, loop.condition, loop.step) == (None, None, None)


def test_locations_and_type_annotations_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        IntLiteral(42, 7, 12)
    with pytest.raises(TypeError):
        IntLiteral(42, "int")


def test_decoded_string_literal_preserves_escapes_and_unicode() -> None:
    value = 'line one\n\t"quoted" \\ café'
    assert StringLiteral(value).value == value
