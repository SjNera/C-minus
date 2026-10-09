"""Module 3 tests using hand-built ASTs, independent of the parser."""

from collections.abc import Iterator
from dataclasses import fields

import pytest

import cminus.extras.format_io as format_io
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
    Stmt,
    StringLiteral,
    UnaryOp,
    VarDecl,
    While,
)
from cminus.errors import SemanticError
from cminus.semantic_analyser import SemanticAnalyser, SymbolTable, analyse


BINARY_OPERATORS = (
    "+",
    "-",
    "*",
    "/",
    "%",
    "<",
    "<=",
    ">",
    ">=",
    "==",
    "!=",
    "&&",
    "||",
)


def function(
    name: str,
    statements: list[Stmt] | None = None,
    *,
    return_type: str = "int",
    params: list[Param] | None = None,
    line: int = 1,
) -> FunctionDecl:
    return FunctionDecl(
        return_type,
        name,
        params if params is not None else [],
        Block(statements if statements is not None else []),
        line=line,
        column=2,
    )


def program(*statements: Stmt, functions: tuple[FunctionDecl, ...] = ()) -> Program:
    return Program([function("main", list(statements)), *functions], line=1, column=1)


def assert_error(
    tree: Program, message: str, line: int, column: int
) -> SemanticError:
    with pytest.raises(SemanticError) as caught:
        analyse(tree)
    error = caught.value
    assert error.message == message
    assert (error.line, error.column) == (line, column)
    return error


def expressions(node: Node) -> Iterator[Expr]:
    if isinstance(node, Expr):
        yield node
    for field in fields(node):
        value = getattr(node, field.name)
        if isinstance(value, Node):
            yield from expressions(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Node):
                    yield from expressions(item)


def literal(type_name: str) -> Expr:
    if type_name == "int":
        return IntLiteral(2)
    if type_name == "bool":
        return BoolLiteral(True)
    if type_name == "string":
        return StringLiteral("text")
    return Call("noop")


@pytest.fixture
def printf_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(format_io, "validate_printf", raising=False)


def test_factorial_forward_call_and_recursion() -> None:
    factorial = function(
        "factorial",
        [
            If(
                BinaryOp("<=", Identifier("n"), IntLiteral(1)),
                Return(IntLiteral(1)),
                Return(
                    BinaryOp(
                        "*",
                        Identifier("n"),
                        Call("factorial", [BinaryOp("-", Identifier("n"), IntLiteral(1))]),
                    )
                ),
            )
        ],
        params=[Param("int", "n", line=3, column=15)],
        line=3,
    )
    tree = program(
        Return(Call("factorial", [IntLiteral(5)])), functions=(factorial,)
    )
    symbols = analyse(tree)
    assert isinstance(symbols, SymbolTable)
    signature = symbols.lookup_function("factorial")
    assert signature is not None
    assert signature.type_name == "int"
    assert [(p.type_name, p.name) for p in signature.params] == [("int", "n")]
    assert symbols.lookup_function("missing") is None
    assert [scope.name for scope in symbols.all_scopes] == [
        "global", "main", "factorial"
    ]
    assert symbols.all_scopes[-1].symbols["n"].kind == "param"
    assert all(expr.resolved_type is not None for expr in expressions(tree))


def test_mutually_recursive_functions() -> None:
    first = function("first", [Return(Call("second"))])
    second = function("second", [Return(Call("first"))])
    analyse(program(Return(Call("first")), functions=(first, second)))


def test_dump_is_readable_and_deterministic() -> None:
    tree = program(
        VarDecl("int", "x", line=4),
        Block([VarDecl("bool", "x", line=5)]),
    )
    expected = (
        "scope: global\n"
        "  function printf(string fmt, ...) -> int   [builtin]\n"
        "  function main() -> int   [line 1]\n"
        "scope: main\n"
        "  var x: int   [line 4]\n"
        "scope: main/block1\n"
        "  var x: bool   [line 5]"
    )
    assert analyse(tree).dump() == expected
    assert analyse(tree).dump() == expected


@pytest.mark.parametrize("later_declaration", [False, True])
def test_undeclared_or_used_before_declaration(later_declaration: bool) -> None:
    statements: list[Stmt] = [ExprStmt(Identifier("count", line=7, column=9))]
    if later_declaration:
        statements.append(VarDecl("int", "count", line=8))
    assert_error(
        program(*statements),
        "variable 'count' is used before it is declared",
        7,
        9,
    )


def test_variable_is_not_visible_in_its_initializer() -> None:
    assert_error(
        program(
            VarDecl(
                "int", "x", BinaryOp("+", Identifier("x", line=4, column=11), IntLiteral(1))
            )
        ),
        "variable 'x' is used before it is declared",
        4,
        11,
    )


def test_redeclaration_reports_first_line() -> None:
    assert_error(
        program(VarDecl("int", "x", line=4), VarDecl("bool", "x", line=8, column=3)),
        "redeclaration of 'x' in the same scope (first declared at line 4)",
        8,
        3,
    )


def test_shadowing_and_outer_binding_in_initializer() -> None:
    initializer = Identifier("x")
    inner_use = Identifier("x")
    outer_use = Identifier("x")
    tree = program(
        VarDecl("int", "x", IntLiteral(1)),
        Block([VarDecl("bool", "x", initializer), ExprStmt(inner_use)]),
        ExprStmt(outer_use),
    )
    symbols = analyse(tree)
    assert initializer.resolved_type == "int"
    assert inner_use.resolved_type == "bool"
    assert outer_use.resolved_type == "int"
    assert symbols.all_scopes[2].parent is symbols.all_scopes[1]


def test_parameter_redeclared_in_top_level_body() -> None:
    helper = function(
        "helper",
        [VarDecl("int", "n", line=6, column=3)],
        params=[Param("int", "n", line=3)],
    )
    assert_error(
        program(functions=(helper,)),
        "redeclaration of 'n' in the same scope (first declared at line 3)",
        6,
        3,
    )


def test_duplicate_parameters() -> None:
    helper = function(
        "helper",
        params=[Param("int", "n", line=3), Param("bool", "n", line=4, column=12)],
    )
    assert_error(
        program(functions=(helper,)),
        "redeclaration of 'n' in the same scope (first declared at line 3)",
        4,
        12,
    )


@pytest.mark.parametrize("type_name", ["void", "string", "float"])
@pytest.mark.parametrize("kind", ["variable", "parameter"])
def test_invalid_declaration_types(type_name: str, kind: str) -> None:
    if kind == "variable":
        tree = program(VarDecl(type_name, "x", line=8, column=4))
    else:
        tree = program(
            functions=(
                function("f", params=[Param(type_name, "x", line=8, column=4)]),
            )
        )
    assert_error(tree, f"{kind} 'x' cannot have type '{type_name}'", 8, 4)


@pytest.mark.parametrize("type_name", ["string", "float"])
def test_invalid_function_return_type(type_name: str) -> None:
    assert_error(
        program(functions=(function("f", return_type=type_name, line=6),)),
        f"function 'f' has invalid return type '{type_name}'",
        6,
        2,
    )


def test_duplicate_functions() -> None:
    assert_error(
        program(functions=(function("f", line=3), function("f", line=10))),
        "duplicate function 'f' (first declared at line 3)",
        10,
        2,
    )


def test_printf_cannot_be_redefined() -> None:
    assert_error(
        program(functions=(function("printf", line=5),)),
        "duplicate function 'printf' (first declared at a built-in)",
        5,
        2,
    )


@pytest.mark.parametrize("assignment", [False, True])
def test_function_name_cannot_be_used_as_variable(assignment: bool) -> None:
    identifier = Identifier("f", line=5, column=7)
    expr = Assign(identifier, IntLiteral(1)) if assignment else identifier
    assert_error(
        program(ExprStmt(expr), functions=(function("f"),)),
        "function 'f' cannot be used as a variable",
        5,
        7,
    )


def test_call_to_undeclared_function() -> None:
    assert_error(
        program(ExprStmt(Call("foo", line=12, column=8))),
        "call to undeclared function 'foo'",
        12,
        8,
    )


def test_call_to_variable_that_shadows_a_function() -> None:
    assert_error(
        program(
            VarDecl("int", "f"),
            ExprStmt(Call("f", line=12, column=8)),
            functions=(function("f"),),
        ),
        "cannot call var 'f' of type 'int'",
        12,
        8,
    )


def test_call_to_parameter() -> None:
    helper = function(
        "f",
        [ExprStmt(Call("x", line=12, column=8))],
        params=[Param("bool", "x")],
    )
    assert_error(
        program(functions=(helper,)), "cannot call param 'x' of type 'bool'", 12, 8
    )


@pytest.mark.parametrize("op", BINARY_OPERATORS)
@pytest.mark.parametrize("left_type", ["int", "bool"])
@pytest.mark.parametrize("right_type", ["int", "bool"])
def test_binary_numeric_types(op: str, left_type: str, right_type: str) -> None:
    expr = BinaryOp(op, literal(left_type), literal(right_type))
    analyse(program(ExprStmt(expr)))
    expected_type = "int" if op in ("+", "-", "*", "/", "%") else "bool"
    assert expr.resolved_type == expected_type
    assert expr.left.resolved_type == left_type
    assert expr.right.resolved_type == right_type


@pytest.mark.parametrize("op", BINARY_OPERATORS)
@pytest.mark.parametrize("bad_type", ["string", "void"])
@pytest.mark.parametrize("bad_side", ["left", "right"])
def test_binary_rejects_string_and_void(op: str, bad_type: str, bad_side: str) -> None:
    left_type, right_type = (
        (bad_type, "int") if bad_side == "left" else ("int", bad_type)
    )
    expr = BinaryOp(op, literal(left_type), literal(right_type), line=9, column=6)
    assert_error(
        program(ExprStmt(expr), functions=(function("noop", return_type="void"),)),
        f"operator '{op}' cannot be applied to '{left_type}' and '{right_type}'",
        9,
        6,
    )


@pytest.mark.parametrize("op", ["!", "-"])
@pytest.mark.parametrize("type_name", ["int", "bool"])
def test_unary_numeric_types(op: str, type_name: str) -> None:
    expr = UnaryOp(op, literal(type_name))
    analyse(program(ExprStmt(expr)))
    assert expr.resolved_type == ("bool" if op == "!" else "int")


@pytest.mark.parametrize("op", ["!", "-"])
@pytest.mark.parametrize("type_name", ["string", "void"])
def test_unary_rejects_string_and_void(op: str, type_name: str) -> None:
    assert_error(
        program(
            ExprStmt(UnaryOp(op, literal(type_name), line=9, column=6)),
            functions=(function("noop", return_type="void"),),
        ),
        f"operator '{op}' cannot be applied to '{type_name}'",
        9,
        6,
    )


@pytest.mark.parametrize("unary", [False, True])
def test_unsupported_operator_is_a_semantic_error(unary: bool) -> None:
    if unary:
        expr = UnaryOp("~", IntLiteral(1), line=3, column=4)
    else:
        expr = BinaryOp("&", IntLiteral(1), IntLiteral(2), line=3, column=4)
    assert_error(
        program(ExprStmt(expr)),
        (
            "unsupported unary operator '~'"
            if unary else "unsupported binary operator '&'"
        ),
        3,
        4,
    )


@pytest.mark.parametrize("target_type", ["int", "bool"])
@pytest.mark.parametrize("value_type", ["int", "bool"])
def test_numeric_initialization_and_assignment(
    target_type: str, value_type: str
) -> None:
    assignment = Assign(Identifier("x"), literal(value_type))
    analyse(
        program(VarDecl(target_type, "x", literal(value_type)), ExprStmt(assignment))
    )
    assert assignment.resolved_type == target_type
    assert assignment.target.resolved_type == target_type
    assert assignment.value.resolved_type == value_type


@pytest.mark.parametrize("initializer", [False, True])
def test_assignment_type_mismatch(initializer: bool) -> None:
    value = StringLiteral("text", line=8, column=11)
    if initializer:
        tree = program(VarDecl("int", "a", value))
    else:
        tree = program(
            VarDecl("int", "a"),
            ExprStmt(Assign(Identifier("a"), value, line=8, column=11)),
        )
    assert_error(tree, "cannot assign 'string' to variable 'a' of type 'int'", 8, 11)


def test_chained_assignment_annotates_every_target() -> None:
    inner = Assign(Identifier("b"), IntLiteral(4))
    outer = Assign(Identifier("a"), inner)
    analyse(program(VarDecl("int", "a"), VarDecl("bool", "b"), ExprStmt(outer)))
    assert inner.resolved_type == inner.target.resolved_type == "bool"
    assert outer.resolved_type == outer.target.resolved_type == "int"


@pytest.mark.parametrize("count", [0, 1, 3])
def test_wrong_argument_count(count: int) -> None:
    add = function("add", params=[Param("int", "a"), Param("int", "b")])
    assert_error(
        program(
            ExprStmt(
                Call("add", [IntLiteral(1) for _ in range(count)], line=9, column=4)
            ),
            functions=(add,),
        ),
        f"function 'add' expects 2 arguments but {count} were given",
        9,
        4,
    )


def test_wrong_argument_type() -> None:
    add = function("add", params=[Param("int", "a")])
    assert_error(
        program(
            ExprStmt(Call("add", [StringLiteral("x", line=9, column=12)])),
            functions=(add,),
        ),
        "function 'add' argument 1 expects type 'int', found 'string'",
        9,
        12,
    )


@pytest.mark.parametrize("parameter_type", ["int", "bool"])
@pytest.mark.parametrize("argument_type", ["int", "bool"])
def test_numeric_call_conversions(parameter_type: str, argument_type: str) -> None:
    callee = function("f", params=[Param(parameter_type, "x")], return_type="bool")
    call = Call("f", [literal(argument_type)])
    analyse(program(ExprStmt(call), functions=(callee,)))
    assert call.resolved_type == "bool"


def test_standalone_void_call_is_allowed() -> None:
    call = Call("noop")
    analyse(
        program(
            ExprStmt(call),
            functions=(function("noop", [Return()], return_type="void"),),
        )
    )
    assert call.resolved_type == "void"


@pytest.mark.parametrize(
    "context",
    ["initializer", "assignment", "condition", "argument", "return", "printf"],
)
def test_void_value_is_rejected(context: str) -> None:
    call = Call("noop", line=9, column=12)
    helpers = (
        function("noop", return_type="void"),
        function("f", params=[Param("int", "x")]),
    )
    if context == "initializer":
        statements = [VarDecl("int", "x", call)]
    elif context == "assignment":
        statements = [VarDecl("int", "x"), ExprStmt(Assign(Identifier("x"), call))]
    elif context == "condition":
        statements = [If(call, Block())]
    elif context == "argument":
        statements = [ExprStmt(Call("f", [call]))]
    elif context == "printf":
        statements = [ExprStmt(Call("printf", [StringLiteral("%d"), call]))]
    else:
        statements = [Return(call)]
    assert_error(
        program(*statements, functions=helpers),
        "cannot use the result of void function 'noop' in an expression",
        9,
        12,
    )


@pytest.mark.parametrize("kind", ["if", "while", "do-while", "for"])
def test_string_condition_rejected(kind: str) -> None:
    condition = StringLiteral("text", line=8, column=7)
    if kind == "if":
        statement = If(condition, Block())
    elif kind == "while":
        statement = While(condition, Block())
    elif kind == "do-while":
        statement = DoWhile(Block(), condition)
    else:
        statement = For(None, condition, None, Block())
    assert_error(
        program(statement), "condition must be int or bool, found 'string'", 8, 7
    )


@pytest.mark.parametrize("return_type", ["int", "bool"])
@pytest.mark.parametrize("value_type", ["int", "bool"])
def test_numeric_return_conversions(return_type: str, value_type: str) -> None:
    value = literal(value_type)
    analyse(
        program(functions=(function("f", [Return(value)], return_type=return_type),))
    )
    assert value.resolved_type == value_type


def test_void_function_returning_value() -> None:
    assert_error(
        program(
            functions=(
                function(
                    "f", [Return(IntLiteral(1), line=9, column=3)], return_type="void"
                ),
            )
        ),
        "void function 'f' should not return a value",
        9,
        3,
    )


def test_nonvoid_function_returning_no_value() -> None:
    assert_error(
        program(functions=(function("f", [Return(line=9, column=3)]),)),
        "non-void function 'f' must return a value",
        9,
        3,
    )


def test_return_type_mismatch() -> None:
    assert_error(
        program(Return(StringLiteral("text", line=9, column=10))),
        "function 'main' cannot return 'string' as 'int'",
        9,
        10,
    )


def test_all_paths_return_analysis_is_not_required() -> None:
    analyse(
        program(
            If(BoolLiteral(True), Return(IntLiteral(1))), functions=(function("empty"),)
        )
    )


def test_missing_main() -> None:
    assert_error(
        Program([function("helper")], line=2, column=1),
        "'main' function is not defined",
        2,
        1,
    )


@pytest.mark.parametrize(
    "return_type,params",
    [("void", []), ("bool", []), ("int", [Param("int", "n")])],
)
def test_invalid_main(return_type: str, params: list[Param]) -> None:
    assert_error(
        Program([function("main", return_type=return_type, params=params, line=5)]),
        "'main' function must return int and take no parameters",
        5,
        2,
    )


def test_for_header_and_body_scopes() -> None:
    condition_use = Identifier("i")
    step_use = Identifier("i")
    body_use = Identifier("i")
    outer_use = Identifier("i")
    loop = For(
        VarDecl("int", "i", IntLiteral(0)),
        BinaryOp("<", condition_use, IntLiteral(5)),
        Assign(step_use, BinaryOp("+", Identifier("i"), IntLiteral(1))),
        Block([VarDecl("bool", "i", BoolLiteral(True)), ExprStmt(body_use)]),
    )
    symbols = analyse(program(VarDecl("bool", "i"), loop, ExprStmt(outer_use)))
    assert condition_use.resolved_type == step_use.resolved_type == "int"
    assert body_use.resolved_type == outer_use.resolved_type == "bool"
    assert [scope.name for scope in symbols.all_scopes] == [
        "global", "main", "main/for1", "main/for1/for-body2"
    ]
    assert symbols.all_scopes[3].parent is symbols.all_scopes[2]


def test_for_header_variable_not_visible_after_loop() -> None:
    assert_error(
        program(
            For(VarDecl("int", "i"), None, None, Block()),
            ExprStmt(Identifier("i", line=10, column=4)),
        ),
        "variable 'i' is used before it is declared",
        10,
        4,
    )


def test_for_body_variable_not_visible_in_step() -> None:
    assert_error(
        program(
            For(
                None, None, Identifier("x", line=8, column=20),
                Block([VarDecl("int", "x")]),
            )
        ),
        "variable 'x' is used before it is declared",
        8,
        20,
    )


def test_for_expression_initializer_and_discarded_void_step() -> None:
    init = Assign(Identifier("i"), IntLiteral(0))
    step = Call("noop")
    analyse(
        program(
            VarDecl("int", "i"),
            For(ExprStmt(init), None, step, Block()),
            functions=(function("noop", return_type="void"),),
        )
    )
    assert init.resolved_type == "int"
    assert step.resolved_type == "void"


@pytest.mark.parametrize("kind", ["while", "do-while", "for"])
@pytest.mark.parametrize("braced", [False, True])
def test_loop_body_has_its_own_scope(kind: str, braced: bool) -> None:
    declaration = VarDecl("int", "local")
    body = Block([declaration]) if braced else declaration
    if kind == "while":
        loop = While(BoolLiteral(True), body)
    elif kind == "do-while":
        loop = DoWhile(body, IntLiteral(0))
    else:
        loop = For(None, None, None, body)
    assert_error(
        program(loop, ExprStmt(Identifier("local", line=10, column=3))),
        "variable 'local' is used before it is declared",
        10,
        3,
    )


def test_do_while_condition_cannot_see_body_local() -> None:
    assert_error(
        program(
            DoWhile(Block([VarDecl("int", "x")]), Identifier("x", line=9, column=8))
        ),
        "variable 'x' is used before it is declared",
        9,
        8,
    )


def test_if_branches_have_independent_block_scopes() -> None:
    tree = program(
        If(
            BoolLiteral(True), Block([VarDecl("int", "x")]),
            Block([VarDecl("bool", "x")]),
        )
    )
    symbols = analyse(tree)
    assert symbols.all_scopes[2].symbols["x"].type_name == "int"
    assert symbols.all_scopes[3].symbols["x"].type_name == "bool"


@pytest.mark.parametrize("fmt,args", [
    ("hello", []),
    ("100%%", []),
    ("%%%d", [IntLiteral(2)]),
    ("%d", [BoolLiteral(True)]),
    ("%i", [IntLiteral(2)]),
    ("%c", [BoolLiteral(False)]),
    ("%s", [StringLiteral("text")]),
    (
        "%d %i %c %s %%",
        [IntLiteral(1), BoolLiteral(True), IntLiteral(65), StringLiteral("text")],
    ),
])
def test_printf_valid_formats(
    printf_fallback: None, fmt: str, args: list[Expr]
) -> None:
    call = Call("printf", [StringLiteral(fmt), *args])
    analyse(program(ExprStmt(call)))
    assert call.resolved_type == "int"
    assert call.args[0].resolved_type == "string"
    assert all(arg.resolved_type is not None for arg in call.args)


@pytest.mark.parametrize("fmt,args,message", [
    ("%d", [], "printf format expects 1 arguments but 0 were given"),
    ("%%", [IntLiteral(1)], "printf format expects 0 arguments but 1 were given"),
    ("%s", [IntLiteral(1)], "printf specifier '%s' expects 'string', found 'int'"),
    (
        "%d", [StringLiteral("x")],
        "printf specifier '%d' expects int or bool, found 'string'",
    ),
    (
        "%i", [StringLiteral("x")],
        "printf specifier '%i' expects int or bool, found 'string'",
    ),
    (
        "%c", [StringLiteral("x")],
        "printf specifier '%c' expects int or bool, found 'string'",
    ),
    ("%f", [], "unsupported printf format specifier '%f'"),
    ("%", [], "incomplete printf format specifier '%'"),
])
def test_printf_invalid_formats(
    printf_fallback: None, fmt: str, args: list[Expr], message: str
) -> None:
    assert_error(
        program(ExprStmt(Call("printf", [StringLiteral(fmt), *args], line=12, column=4))),
        message,
        12,
        4,
    )


def test_printf_requires_format_argument() -> None:
    assert_error(
        program(ExprStmt(Call("printf", line=12, column=4))),
        "function 'printf' expects at least 1 argument but 0 were given",
        12,
        4,
    )


def test_printf_format_must_be_literal() -> None:
    assert_error(
        program(ExprStmt(Call("printf", [IntLiteral(1, line=12, column=11)]))),
        "first argument to 'printf' must be a string literal",
        12,
        11,
    )


def test_printf_uses_module7_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[tuple[str, list[str], int, int]] = []

    def validate(fmt: str, arg_types: list[str], line: int, column: int) -> None:
        received.append((fmt, arg_types, line, column))

    monkeypatch.setattr(format_io, "validate_printf", validate, raising=False)
    call = Call(
        "printf", [StringLiteral("%d %s"), BoolLiteral(True), StringLiteral("x")],
        line=8, column=4,
    )
    analyse(program(ExprStmt(call)))
    assert received == [("%d %s", ["bool", "string"], 8, 4)]
    assert call.resolved_type == "int"


def test_printf_propagates_module7_error(monkeypatch: pytest.MonkeyPatch) -> None:
    error = SemanticError("module 7 format mismatch", 15, 3)

    def validate(fmt: str, arg_types: list[str], line: int, column: int) -> None:
        raise error

    monkeypatch.setattr(format_io, "validate_printf", validate, raising=False)
    with pytest.raises(SemanticError) as caught:
        analyse(program(ExprStmt(Call("printf", [StringLiteral("text")]))))
    assert caught.value is error


def test_every_expression_is_annotated(printf_fallback: None) -> None:
    helper = function("helper", [Return(Identifier("n"))], params=[Param("int", "n")])
    noop = function("noop", [Return()], return_type="void")
    tree = program(
        VarDecl("int", "x", Call("helper", [Call("helper", [IntLiteral(2)])])),
        VarDecl("bool", "flag", UnaryOp("!", BoolLiteral(False))),
        If(
            Call("helper", [Identifier("flag")]),
            Block([
                ExprStmt(
                    Assign(Identifier("x"), BinaryOp("/", Identifier("x"), IntLiteral(2)))
                )
            ]),
            ExprStmt(Call("noop")),
        ),
        While(
            Call("helper", [Identifier("x")]),
            Block([ExprStmt(Assign(Identifier("x"), IntLiteral(0)))]),
        ),
        DoWhile(ExprStmt(Call("noop")), BoolLiteral(False)),
        For(
            VarDecl("int", "i", IntLiteral(0)),
            BinaryOp("<", Identifier("i"), IntLiteral(3)),
            Assign(Identifier("i"), BinaryOp("+", Identifier("i"), IntLiteral(1))),
            Block([
                ExprStmt(Call("printf", [
                    StringLiteral("%d %s %%"),
                    BinaryOp("%", Identifier("x"), IntLiteral(2)),
                    StringLiteral("done"),
                ]))
            ]),
        ),
        Return(UnaryOp("-", Identifier("x"))),
        functions=(helper, noop),
    )
    analyse(tree)
    nodes = list(expressions(tree))
    assert {type(node) for node in nodes} == {
        IntLiteral, BoolLiteral, StringLiteral, Identifier,
        Assign, BinaryOp, UnaryOp, Call,
    }
    assert all(
        node.resolved_type in ("int", "bool", "string", "void") for node in nodes
    )
    assert all(
        node.target.resolved_type is not None
        for node in nodes if isinstance(node, Assign)
    )


def test_first_error_stops_analysis_without_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    second = Identifier("second", line=9)
    assert_error(
        program(ExprStmt(Identifier("first", line=8, column=3)), ExprStmt(second)),
        "variable 'first' is used before it is declared",
        8,
        3,
    )
    assert second.resolved_type is None
    analyse(program())
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_analyser_reuse_resets_state_after_success_and_error() -> None:
    analyser = SemanticAnalyser()
    first = analyser.analyse(program(VarDecl("int", "x"), functions=(function("old"),)))
    with pytest.raises(SemanticError):
        analyser.analyse(program(Block([ExprStmt(Identifier("missing"))])))
    assert analyser.current_scope is analyser.symbol_table.global_scope
    assert analyser.current_function is None
    second = analyser.analyse(program(Block([VarDecl("bool", "fresh")])))
    assert second.lookup_function("old") is None
    assert first.lookup_function("old") is not None
    assert first.all_scopes[1].symbols["x"].type_name == "int"
    assert second.all_scopes[-1].name == "main/block1"


def test_function_bodies_do_not_share_local_bindings() -> None:
    helper = function("helper", [VarDecl("int", "private")])
    tree = Program(
        [
            helper,
            function("main", [Return(Identifier("private", line=9, column=12))]),
        ]
    )
    assert_error(tree, "variable 'private' is used before it is declared", 9, 12)


def test_sibling_blocks_do_not_share_local_bindings() -> None:
    assert_error(
        program(
            Block([VarDecl("int", "local")]),
            Block([ExprStmt(Identifier("local", line=8, column=5))]),
        ),
        "variable 'local' is used before it is declared",
        8,
        5,
    )


def test_parameters_can_be_shadowed_in_nested_blocks() -> None:
    inner_use, parameter_use = Identifier("n"), Identifier("n")
    helper = function(
        "helper",
        [Block([VarDecl("bool", "n"), ExprStmt(inner_use)]), Return(parameter_use)],
        params=[Param("int", "n")],
    )
    analyse(program(functions=(helper,)))
    assert inner_use.resolved_type == "bool"
    assert parameter_use.resolved_type == "int"


@pytest.mark.parametrize("kind", ["if", "while", "for", "after-return"])
def test_unreachable_statements_are_still_checked(kind: str) -> None:
    invalid = ExprStmt(Identifier("missing", line=7, column=9))
    if kind == "if":
        statements = [If(BoolLiteral(True), Return(IntLiteral(0)), invalid)]
    elif kind == "while":
        statements = [While(BoolLiteral(False), invalid)]
    elif kind == "for":
        statements = [For(None, BoolLiteral(False), None, invalid)]
    else:
        statements = [Return(IntLiteral(0)), invalid]
    assert_error(
        program(*statements), "variable 'missing' is used before it is declared", 7, 9
    )


def test_signature_errors_are_reported_before_function_bodies() -> None:
    first_expression = Identifier("missing", line=3, column=5)
    tree = program(
        ExprStmt(first_expression),
        functions=(function("invalid", return_type="float", line=8),),
    )
    assert_error(tree, "function 'invalid' has invalid return type 'float'", 8, 2)
    assert first_expression.resolved_type is None


def test_undeclared_assignment_target_stops_before_evaluating_value() -> None:
    value = IntLiteral(3)
    assert_error(
        program(ExprStmt(Assign(Identifier("missing", line=6, column=4), value))),
        "variable 'missing' is used before it is declared",
        6,
        4,
    )
    assert value.resolved_type is None


@pytest.mark.parametrize("part", ["initializer", "condition", "step", "body"])
def test_for_errors_restore_enclosing_scope_and_function(part: str) -> None:
    invalid = Identifier("missing", line=8, column=6)
    loop = For(
        ExprStmt(invalid) if part == "initializer" else VarDecl("int", "i"),
        invalid if part == "condition" else BoolLiteral(True),
        invalid if part == "step" else None,
        Block([ExprStmt(invalid)]) if part == "body" else Block(),
    )
    analyser = SemanticAnalyser()
    with pytest.raises(SemanticError) as caught:
        analyser.analyse(program(Block([loop])))
    assert caught.value.message == "variable 'missing' is used before it is declared"
    assert (caught.value.line, caught.value.column) == (8, 6)
    assert analyser.current_scope is analyser.symbol_table.global_scope
    assert analyser.current_function is None
    assert analyser.lookup("i") is None


def test_builtin_printf_obeys_normal_lexical_shadowing() -> None:
    assert_error(
        program(
            VarDecl("bool", "printf"),
            ExprStmt(Call("printf", [StringLiteral("hello")], line=8, column=4)),
        ),
        "cannot call var 'printf' of type 'bool'",
        8,
        4,
    )


def test_printf_builtin_becomes_visible_after_shadowing_scope_ends() -> None:
    call = Call("printf", [StringLiteral("hello")])
    symbols = analyse(program(Block([VarDecl("int", "printf")]), ExprStmt(call)))
    assert call.resolved_type == "int"
    signature = symbols.lookup_function("printf")
    assert signature is not None and signature.builtin and signature.variadic
    assert [(param.type_name, param.name) for param in signature.params] == [
        ("string", "fmt")
    ]


@pytest.mark.parametrize("fmt", ["", "%%d", "%%%%", "%%s %%i %%c"])
def test_printf_escaped_specifiers_consume_no_arguments(
    printf_fallback: None,
    fmt: str,
) -> None:
    call = Call("printf", [StringLiteral(fmt)])
    analyse(program(ExprStmt(call)))
    assert call.resolved_type == "int"


def test_printf_invalid_argument_stops_before_format_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []

    def validate(fmt: str, arg_types: list[str], line: int, column: int) -> None:
        received.append(fmt)

    monkeypatch.setattr(format_io, "validate_printf", validate, raising=False)
    assert_error(
        program(
            ExprStmt(
                Call(
                    "printf",
                    [
                        StringLiteral("%d"),
                        Identifier("missing", line=10, column=16),
                    ],
                )
            )
        ),
        "variable 'missing' is used before it is declared",
        10,
        16,
    )
    assert received == []


def test_unsupported_ast_node_reports_its_source_location() -> None:
    analyser = SemanticAnalyser()
    with pytest.raises(SemanticError) as caught:
        analyser.visit(Node(line=11, column=3))
    assert caught.value.message == "unsupported syntax node 'Node'"
    assert (caught.value.line, caught.value.column) == (11, 3)


def test_return_outside_function_reports_its_source_location() -> None:
    analyser = SemanticAnalyser()
    with pytest.raises(SemanticError) as caught:
        analyser.visit(Return(IntLiteral(0), line=4, column=2))
    assert caught.value.message == "return statement outside a function"
    assert (caught.value.line, caught.value.column) == (4, 2)
