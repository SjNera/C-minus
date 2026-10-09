"""Lexical lookup, declaration errors, and retained scopes."""

import pytest

from cminus.ast_nodes import Param
from cminus.errors import SemanticError
from cminus.semantic_analyser import Scope, SemanticAnalyser, Symbol, SymbolTable


def test_lookup_uses_nearest_binding_and_never_searches_child_scopes() -> None:
    global_scope = Scope("global")
    outer = Scope("main", global_scope)
    inner = Scope("main/block", outer)
    sibling = Scope("main/sibling", outer)
    global_symbol = Symbol("helper", "function", "int", 1, 1)
    outer_symbol = Symbol("x", "var", "int", 3, 2)
    inner_symbol = Symbol("x", "var", "bool", 5, 2)
    local_symbol = Symbol("local", "var", "int", 6, 2)
    global_scope.symbols["helper"] = global_symbol
    outer.symbols["x"] = outer_symbol
    inner.symbols.update(x=inner_symbol, local=local_symbol)

    assert inner.lookup("x") is inner_symbol
    assert sibling.lookup("x") is outer_symbol
    assert inner.lookup("helper") is global_symbol
    assert sibling.lookup("local") is None
    assert outer.lookup("local") is None
    assert inner.lookup("missing") is None


def test_symbol_and_scope_default_collections_are_independent() -> None:
    first, second = Symbol("a", "function", "int", 1, 1), Symbol(
        "b", "function", "int", 2, 1
    )
    first_scope, second_scope = Scope("a"), Scope("b")
    first.params.append(Param("int", "n"))
    first_scope.symbols["a"] = first

    assert second.params == []
    assert second_scope.symbols == {}


def test_function_lookup_only_returns_global_function_signatures() -> None:
    table = SymbolTable()
    function = Symbol("helper", "function", "bool", 2, 1)
    table.global_scope.symbols.update(
        helper=function,
        value=Symbol("value", "var", "int", 3, 1),
    )
    child = Scope("main", table.global_scope)
    child.symbols.update(
        helper=Symbol("helper", "var", "int", 4, 1),
        local=Symbol("local", "function", "int", 5, 1),
    )
    table.all_scopes.append(child)

    assert table.lookup_function("helper") is function
    assert table.lookup_function("value") is None
    assert table.lookup_function("local") is None
    assert table.lookup_function("missing") is None


def test_duplicate_declaration_preserves_original_symbol() -> None:
    analyser = SemanticAnalyser()
    original = Symbol("x", "var", "int", 3, 5)
    analyser.declare(original)

    with pytest.raises(SemanticError) as caught:
        analyser.declare(Symbol("x", "param", "bool", 8, 12))

    assert (
        caught.value.message
        == "redeclaration of 'x' in the same scope (first declared at line 3)"
    )
    assert (caught.value.line, caught.value.column) == (8, 12)
    assert analyser.lookup("x") is original


def test_popping_a_scope_restores_lookup_and_retains_scope_history() -> None:
    analyser = SemanticAnalyser()
    outer = Symbol("x", "var", "int", 1, 1)
    analyser.declare(outer)
    child = analyser.push_scope("child")
    inner = Symbol("x", "var", "bool", 2, 1)
    analyser.declare(inner)
    assert analyser.lookup("x") is inner

    analyser.pop_scope()
    assert analyser.current_scope is analyser.symbol_table.global_scope
    assert analyser.lookup("x") is outer
    assert analyser.symbol_table.all_scopes == [analyser.current_scope, child]
    assert child.parent is analyser.current_scope
    assert child.symbols["x"] is inner


def test_global_scope_cannot_be_popped() -> None:
    analyser = SemanticAnalyser()
    with pytest.raises(RuntimeError, match="cannot pop the global scope"):
        analyser.pop_scope()
    assert analyser.current_scope is analyser.symbol_table.global_scope


def test_symbol_dump_includes_function_parameters_and_local_kinds() -> None:
    analyser = SemanticAnalyser()
    analyser.declare(
        Symbol("helper", "function", "bool", 2, 1, params=[Param("int", "n")])
    )
    analyser.push_scope("helper")
    analyser.declare(Symbol("n", "param", "int", 2, 15))
    analyser.declare(Symbol("ready", "var", "bool", 3, 5))
    expected = (
        "scope: global\n"
        "  function helper(int n) -> bool   [line 2]\n"
        "scope: helper\n"
        "  param n: int   [line 2]\n"
        "  var ready: bool   [line 3]"
    )
    assert analyser.symbol_table.dump() == expected
    assert analyser.symbol_table.dump() == expected
