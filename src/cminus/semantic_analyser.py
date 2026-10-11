"""Module 3 - semantic analysis and symbol tables for C-Minus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from cminus.ast_nodes import (
    TYPE_BOOL,
    TYPE_INT,
    TYPE_STRING,
    TYPE_VOID,
    Assign,
    BinaryOp,
    Block,
    BoolLiteral,
    Break,
    Call,
    Continue,
    DoWhile,
    Expr,
    ExprStmt,
    For,
    FunctionDecl,
    FunctionPrototype,
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
from cminus.runtime import c_int_div, c_int_mod
from cminus.types import is_numeric as _is_numeric, is_pointer, is_scalar


@dataclass
class Symbol:
    """A function, parameter, or variable declaration."""

    name: str
    kind: str
    type_name: str
    line: int
    column: int
    params: list[Param] = field(default_factory=list)
    variadic: bool = False
    builtin: bool = False
    binding_id: int | None = field(default=None, kw_only=True)
    is_global: bool = field(default=False, kw_only=True)
    defined: bool = field(default=False, kw_only=True)
    initial_value: int | bool | None = field(default=None, kw_only=True)
    address_taken: bool = field(default=False, kw_only=True)
    initial_target: int | None = field(default=None, kw_only=True)


@dataclass
class Scope:
    """Declarations in one lexical scope, linked to its parent."""

    name: str
    parent: Scope | None = None
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def lookup(self, name: str) -> Symbol | None:
        """Find the nearest declaration, including enclosing scopes."""
        scope: Scope | None = self
        while scope is not None:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None


class SymbolTable:
    """Keep the global signatures and every scope in creation order."""

    def __init__(self) -> None:
        self.global_scope = Scope("global")
        self.all_scopes: list[Scope] = [self.global_scope]
        self.bindings: dict[int, Symbol] = {}

    def lookup_function(self, name: str) -> Symbol | None:
        """Return a global function signature, or None if absent."""
        symbol = self.global_scope.symbols.get(name)
        return (
            symbol
            if symbol is not None and symbol.kind == "function"
            else None
        )

    def dump(self) -> str:
        """Render declarations deterministically for --dump-symbols."""
        lines: list[str] = []
        for scope in self.all_scopes:
            lines.append(f"scope: {scope.name}")
            for symbol in scope.symbols.values():
                if symbol.kind == "function":
                    params = [
                        f"{param.type_name} {param.name}".rstrip()
                        for param in symbol.params
                    ]
                    if symbol.variadic:
                        params.append("...")
                    declaration = (
                        f"function {symbol.name}({', '.join(params)})"
                        f" -> {symbol.type_name}"
                    )
                else:
                    declaration = (
                        f"{symbol.kind} {symbol.name}: {symbol.type_name}"
                    )
                location = (
                    "builtin" if symbol.builtin else f"line {symbol.line}"
                )
                lines.append(f"  {declaration}   [{location}]")
        return "\n".join(lines)


def _basic_printf_check(
    fmt: str, arg_types: list[str], line: int, column: int
) -> None:
    """Check the supported printf specifiers when Module 7 is unavailable."""
    specifiers: list[str] = []
    index = 0
    while index < len(fmt):
        if fmt[index] != "%":
            index += 1
            continue
        index += 1
        if index == len(fmt):
            raise SemanticError(
                "incomplete printf format specifier '%'", line, column
            )
        specifier = fmt[index]
        index += 1
        if specifier == "%":
            continue
        if specifier not in ("d", "i", "c", "s"):
            raise SemanticError(
                f"unsupported printf format specifier '%{specifier}'",
                line,
                column,
            )
        specifiers.append(specifier)

    if len(specifiers) != len(arg_types):
        raise SemanticError(
            f"printf format expects {len(specifiers)} arguments"
            f" but {len(arg_types)} were given",
            line,
            column,
        )
    for specifier, type_name in zip(specifiers, arg_types):
        valid = (
            type_name == TYPE_STRING
            if specifier == "s"
            else _is_numeric(type_name)
        )
        if not valid:
            expected = "'string'" if specifier == "s" else "int or bool"
            raise SemanticError(
                f"printf specifier '%{specifier}' expects {expected},"
                f" found '{type_name}'",
                line,
                column,
            )


def _is_assignable(target_type: str, value_type: str) -> bool:
    """Keep pointer targets exact and preserve C's boolean conversions."""
    if target_type == TYPE_BOOL:
        return is_scalar(value_type)
    if is_pointer(target_type):
        return target_type == value_type
    return _is_numeric(target_type) and _is_numeric(value_type)


def is_null_constant(node: Expr) -> bool:
    """The literal zero is the supported null-pointer spelling."""
    return isinstance(node, IntLiteral) and node.value == 0


class SemanticAnalyser:
    """Resolve declarations and annotate expression types in two passes."""

    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.current_scope = self.symbol_table.global_scope
        self.current_function: FunctionDecl | None = None
        self._scope_count = 0
        self._visible_functions: set[str] = {"printf"}
        self._initializing: set[int] = set()
        self._loop_depth = 0
        self._visible_globals: set[int] = set()

    def analyse(self, program: Program) -> SymbolTable:
        """Analyse a program with fresh state, raising the first semantic error."""
        self.symbol_table = SymbolTable()
        self.current_scope = self.symbol_table.global_scope
        self.current_function = None
        self._scope_count = 0
        self._visible_functions = {"printf"}
        self._initializing = set()
        self._loop_depth = 0
        self._visible_globals = set()
        self.declare(
            Symbol(
                "printf",
                "function",
                TYPE_INT,
                0,
                0,
                params=[Param(TYPE_STRING, "fmt")],
                variadic=True,
                builtin=True,
                defined=True,
            )
        )
        self.visit(program)
        return self.symbol_table

    def visit(self, node: Node) -> str | None:
        """Dispatch to the visitor for the concrete AST node class."""
        visitor = getattr(self, f"visit_{type(node).__name__}", None)
        if visitor is None:
            self._error(
                f"unsupported syntax node '{type(node).__name__}'", node
            )
        return visitor(node)

    def push_scope(self, name: str) -> Scope:
        """Enter and retain a new child scope."""
        scope = Scope(name, self.current_scope)
        self.symbol_table.all_scopes.append(scope)
        self.current_scope = scope
        return scope

    def pop_scope(self) -> None:
        """Return to the enclosing scope."""
        parent = self.current_scope.parent
        if parent is None:
            raise RuntimeError("cannot pop the global scope")
        self.current_scope = parent

    def declare(self, symbol: Symbol) -> Symbol:
        """Declare a symbol after checking for a same-scope redeclaration."""
        previous = self.current_scope.symbols.get(symbol.name)
        if previous is not None:
            raise SemanticError(
                f"redeclaration of '{symbol.name}' in the same scope"
                f" (first declared at line {previous.line})",
                symbol.line,
                symbol.column,
            )
        symbol.binding_id = len(self.symbol_table.bindings)
        self.symbol_table.bindings[symbol.binding_id] = symbol
        self.current_scope.symbols[symbol.name] = symbol
        return symbol

    def lookup(self, name: str) -> Symbol | None:
        """Look up a name with normal lexical shadowing."""
        return self.current_scope.lookup(name)

    def _error(self, message: str, node: Node) -> NoReturn:
        """Report an error at the offending AST node."""
        raise SemanticError(message, node.line, node.column)

    def _resolve(self, node: Expr, type_name: str) -> str:
        """Record and return an expression's resolved type."""
        node.resolved_type = type_name
        return type_name

    def _expression_type(self, node: Expr, *, allow_void: bool = False) -> str:
        """Check an expression, rejecting a void result when a value is needed."""
        type_name = self.visit(node)
        if type_name is None:
            self._error("expected an expression", node)
        if type_name == TYPE_VOID and not allow_void:
            if isinstance(node, Call):
                self._error(
                    f"cannot use the result of void function '{node.callee}'"
                    " in an expression",
                    node,
                )
            self._error("cannot use a void value in an expression", node)
        return type_name

    def _check_condition(self, condition: Expr) -> None:
        """Require a scalar condition, including a pointer's null/non-null test."""
        type_name = self._expression_type(condition)
        if not is_scalar(type_name):
            self._error(
                f"condition must be int or bool, found '{type_name}'",
                condition,
            )

    def _check_declaration_type(
        self, type_name: str, kind: str, node: Node
    ) -> None:
        """Limit storage to numeric values and their first-level pointers."""
        if not is_scalar(type_name):
            self._error(f"{kind} cannot have type '{type_name}'", node)

    def _visit_statements(self, block: Block) -> None:
        """Visit a block's contents in the current scope."""
        for statement in block.statements:
            self.visit(statement)

    def _push_child_scope(self, label: str) -> None:
        """Give nested scopes stable, unique names."""
        self._scope_count += 1
        self.push_scope(
            f"{self.current_scope.name}/{label}{self._scope_count}"
        )

    def _visit_scoped_statement(self, statement: Stmt, label: str) -> None:
        """Give a nested block or loop body exactly one child scope."""
        self._push_child_scope(label)
        try:
            if isinstance(statement, Block):
                self._visit_statements(statement)
            else:
                self.visit(statement)
        finally:
            self.pop_scope()

    def _visit_loop_body(self, statement: Stmt, label: str) -> None:
        """Keep jump validation local to the enclosing loop body."""
        self._loop_depth += 1
        try:
            self._visit_scoped_statement(statement, label)
        finally:
            self._loop_depth -= 1

    def visit_Program(self, node: Program) -> None:
        """Collect bindings, then check bodies in C declaration order."""
        for declaration in node.declarations:
            if isinstance(declaration, (FunctionDecl, FunctionPrototype)):
                self._declare_function(declaration)
            elif isinstance(declaration, VarDecl):
                self._check_declaration_type(
                    declaration.type_name,
                    f"variable '{declaration.name}'",
                    declaration,
                )
                symbol = self.declare(
                    Symbol(
                        declaration.name,
                        "var",
                        declaration.type_name,
                        declaration.line,
                        declaration.column,
                        is_global=True,
                    )
                )
                declaration.binding_id = symbol.binding_id
            else:
                self._error("expected a top-level declaration", declaration)

        main = self.symbol_table.lookup_function("main")
        if main is None or not main.defined:
            self._error("'main' function is not defined", node)
        if main.type_name != TYPE_INT or main.params:
            raise SemanticError(
                "'main' function must return int and take no parameters",
                main.line,
                main.column,
            )
        for declaration in node.declarations:
            if isinstance(declaration, VarDecl):
                self._visible_globals.add(declaration.binding_id)
                self._analyse_global(declaration)
            else:
                self._visible_functions.add(declaration.name)
                if isinstance(declaration, FunctionDecl):
                    self.visit(declaration)

    def _declare_function(
        self, node: FunctionDecl | FunctionPrototype
    ) -> None:
        if node.return_type not in (TYPE_INT, TYPE_BOOL, TYPE_VOID):
            self._error(
                f"function '{node.name}' has invalid return type '{node.return_type}'",
                node,
            )
        for param in node.params:
            self._check_declaration_type(
                param.type_name, f"parameter '{param.name}'", param
            )
        if isinstance(node, FunctionPrototype):
            names = {}
            for param in node.params:
                if param.name and param.name in names:
                    self._error(
                        f"redeclaration of '{param.name}' in the same scope (first declared at line {names[param.name]})",
                        param,
                    )
                if param.name:
                    names[param.name] = param.line
        previous = self.lookup(node.name)
        definition = isinstance(node, FunctionDecl)
        if previous is not None:
            if previous.kind != "function":
                self._error(
                    f"redeclaration of '{node.name}' in the same scope (first declared at line {previous.line})",
                    node,
                )
            if previous.builtin or (definition and previous.defined):
                first = (
                    "a built-in"
                    if previous.builtin
                    else f"line {previous.line}"
                )
                self._error(
                    f"duplicate function '{node.name}' (first declared at {first})",
                    node,
                )
            if previous.type_name != node.return_type or [
                p.type_name for p in previous.params
            ] != [p.type_name for p in node.params]:
                self._error(
                    f"conflicting declaration of function '{node.name}' (first declared at line {previous.line})",
                    node,
                )
            previous.defined = previous.defined or definition
            symbol = previous
        else:
            symbol = self.declare(
                Symbol(
                    node.name,
                    "function",
                    node.return_type,
                    node.line,
                    node.column,
                    params=list(node.params),
                    defined=definition,
                )
            )
        node.binding_id = symbol.binding_id

    def _analyse_global(self, node: VarDecl) -> None:
        symbol = self.symbol_table.bindings[node.binding_id]
        if is_pointer(node.type_name):
            if node.init is None:
                return
            self._check_initializer(node, symbol)
            if is_null_constant(node.init):
                return
            if (
                isinstance(node.init, UnaryOp)
                and node.init.op == "&"
                and isinstance(node.init.operand, Identifier)
            ):
                target = self.symbol_table.bindings[
                    node.init.operand.binding_id
                ]
                if target.is_global:
                    symbol.initial_target = target.binding_id
                    return
            self._error(
                "global pointer initializer must be a global address or 0",
                node.init,
            )
        value = 0
        if node.init is not None:
            self._check_initializer(node, symbol)
            self._check_constant_expression(node.init)
            value = self._constant_value(node.init)
        symbol.initial_value = (
            bool(value) if node.type_name == TYPE_BOOL else int(value)
        )

    def _check_constant_expression(self, node: Expr) -> None:
        if isinstance(node, (IntLiteral, BoolLiteral)):
            return
        if isinstance(node, UnaryOp):
            self._check_constant_expression(node.operand)
            return
        if isinstance(node, BinaryOp):
            self._check_constant_expression(node.left)
            self._check_constant_expression(node.right)
            return
        self._error(
            "global initializer must be an integer constant expression", node
        )

    def _constant_value(self, node: Expr) -> int:
        if isinstance(node, (IntLiteral, BoolLiteral)):
            return int(node.value)
        if isinstance(node, UnaryOp):
            value = self._constant_value(node.operand)
            return -value if node.op == "-" else int(not value)
        left = self._constant_value(node.left)
        if node.op == "&&" and not left:
            return 0
        if node.op == "||" and left:
            return 1
        right = self._constant_value(node.right)
        if node.op in {"/", "%"} and right == 0:
            self._error("division by zero in global initializer", node)
        operations = {
            "+": lambda: left + right,
            "-": lambda: left - right,
            "*": lambda: left * right,
            "/": lambda: c_int_div(left, right),
            "%": lambda: c_int_mod(left, right),
            "<": lambda: int(left < right),
            "<=": lambda: int(left <= right),
            ">": lambda: int(left > right),
            ">=": lambda: int(left >= right),
            "==": lambda: int(left == right),
            "!=": lambda: int(left != right),
            "&&": lambda: int(bool(right)),
            "||": lambda: int(bool(right)),
        }
        return operations[node.op]()

    def visit_FunctionDecl(self, node: FunctionDecl) -> None:
        """Put parameters and top-level body declarations in the same scope."""
        previous_function = self.current_function
        previous_loop_depth = self._loop_depth
        self.current_function = node
        self._loop_depth = 0
        self.push_scope(node.name)
        try:
            for param in node.params:
                self.visit(param)
            self._visit_statements(node.body)
        finally:
            self.pop_scope()
            self.current_function = previous_function
            self._loop_depth = previous_loop_depth

    def visit_Param(self, node: Param) -> None:
        """Declare a validated function parameter."""
        symbol = self.declare(
            Symbol(node.name, "param", node.type_name, node.line, node.column)
        )
        node.binding_id = symbol.binding_id

    def visit_Block(self, node: Block) -> None:
        """Analyse a nested block in a new scope."""
        self._visit_scoped_statement(node, "block")

    def visit_VarDecl(self, node: VarDecl) -> None:
        """Bind at the declarator, rejecting reads of the binding in its initializer."""
        self._check_declaration_type(
            node.type_name, f"variable '{node.name}'", node
        )
        previous = self.current_scope.symbols.get(node.name)
        if previous is not None:
            self._error(
                f"redeclaration of '{node.name}' in the same scope"
                f" (first declared at line {previous.line})",
                node,
            )
        symbol = self.declare(
            Symbol(node.name, "var", node.type_name, node.line, node.column)
        )
        node.binding_id = symbol.binding_id
        self._check_initializer(node, symbol)

    def _check_initializer(self, node: VarDecl, symbol: Symbol) -> None:
        if node.init is not None:
            self._initializing.add(symbol.binding_id)
            try:
                value_type = self._expression_type(node.init)
            finally:
                self._initializing.remove(symbol.binding_id)
            if not self._assignable(node.type_name, value_type, node.init):
                self._error(
                    f"cannot assign '{value_type}' to variable '{node.name}'"
                    f" of type '{node.type_name}'",
                    node.init,
                )

    def _assignable(
        self, target_type: str, value_type: str, value: Expr
    ) -> bool:
        return _is_assignable(target_type, value_type) or (
            is_pointer(target_type) and is_null_constant(value)
        )

    def visit_ExprStmt(self, node: ExprStmt) -> None:
        """Allow a standalone void call whose result is discarded."""
        self._expression_type(node.expr, allow_void=True)

    def visit_If(self, node: If) -> None:
        """Check the condition and both branches, including unreachable code."""
        self._check_condition(node.condition)
        self.visit(node.then_branch)
        if node.else_branch is not None:
            self.visit(node.else_branch)

    def visit_While(self, node: While) -> None:
        """Check a while loop with a child scope for its body."""
        self._check_condition(node.condition)
        self._visit_loop_body(node.body, "while")

    def visit_DoWhile(self, node: DoWhile) -> None:
        """Check a do-while condition outside its body's scope."""
        self._visit_loop_body(node.body, "do-while")
        self._check_condition(node.condition)

    def visit_For(self, node: For) -> None:
        """Keep the header visible to the loop, but not to following statements."""
        self._push_child_scope("for")
        try:
            if node.init is not None:
                self.visit(node.init)
            if node.condition is not None:
                self._check_condition(node.condition)
            if node.step is not None:
                self._expression_type(node.step, allow_void=True)
            self._visit_loop_body(node.body, "for-body")
        finally:
            self.pop_scope()

    def visit_Break(self, node: Break) -> None:
        if not self._loop_depth:
            self._error("break statement outside a loop", node)

    def visit_Continue(self, node: Continue) -> None:
        if not self._loop_depth:
            self._error("continue statement outside a loop", node)

    def visit_Return(self, node: Return) -> None:
        """Validate a return against the enclosing function's return type."""
        function = self.current_function
        if function is None:
            self._error("return statement outside a function", node)
        if function.return_type == TYPE_VOID:
            if node.value is not None:
                self._error(
                    f"void function '{function.name}' should not return a value",
                    node,
                )
            return
        if node.value is None:
            self._error(
                f"non-void function '{function.name}' must return a value",
                node,
            )
        value_type = self._expression_type(node.value)
        if not self._assignable(function.return_type, value_type, node.value):
            self._error(
                f"function '{function.name}' cannot return '{value_type}'"
                f" as '{function.return_type}'",
                node.value,
            )

    def _variable_binding(self, node: Identifier) -> Symbol:
        symbol = self.lookup(node.name)
        if symbol is None:
            self._error(
                f"variable '{node.name}' is used before it is declared", node
            )
        if symbol.kind == "function":
            self._error(
                f"function '{node.name}' cannot be used as a variable", node
            )
        if symbol.is_global and symbol.binding_id not in self._visible_globals:
            self._error(
                f"variable '{node.name}' is used before it is declared", node
            )
        node.binding_id = symbol.binding_id
        return symbol

    def visit_Identifier(self, node: Identifier) -> str:
        """Resolve a variable or parameter through the enclosing scopes."""
        symbol = self._variable_binding(node)
        if symbol.binding_id in self._initializing:
            self._error(
                f"variable '{node.name}' is read in its own initializer", node
            )
        return self._resolve(node, symbol.type_name)

    def visit_Assign(self, node: Assign) -> str:
        """Check an assignment and annotate its target as well as its value."""
        if isinstance(node.target, Identifier):
            symbol = self._variable_binding(node.target)
            node.binding_id = symbol.binding_id
            target_type = self._resolve(node.target, symbol.type_name)
            label = f"variable '{node.target.name}'"
        elif isinstance(node.target, UnaryOp) and node.target.op == "*":
            target_type = self._expression_type(node.target)
            label = "dereferenced pointer"
        else:
            self._error(
                "assignment target must be a variable or dereference",
                node.target,
            )
        value_type = self._expression_type(node.value)
        if not self._assignable(target_type, value_type, node.value):
            self._error(
                f"cannot assign '{value_type}' to {label}"
                f" of type '{target_type}'",
                node,
            )
        return self._resolve(node, target_type)

    def visit_BinaryOp(self, node: BinaryOp) -> str:
        """Type arithmetic, comparison, and logical operators."""
        left_type = self._expression_type(node.left, allow_void=True)
        right_type = self._expression_type(node.right, allow_void=True)
        if node.op in ("+", "-", "*", "/", "%"):
            result_type = TYPE_INT
        elif node.op in ("<", "<=", ">", ">=", "==", "!=", "&&", "||"):
            result_type = TYPE_BOOL
        else:
            self._error(f"unsupported binary operator '{node.op}'", node)
        if (
            node.op in {"&&", "||"}
            and is_scalar(left_type)
            and is_scalar(right_type)
        ):
            return self._resolve(node, result_type)
        if node.op in {"==", "!="} and (
            is_pointer(left_type)
            and (left_type == right_type or is_null_constant(node.right))
            or is_pointer(right_type)
            and is_null_constant(node.left)
        ):
            return self._resolve(node, result_type)
        if not (_is_numeric(left_type) and _is_numeric(right_type)):
            self._error(
                f"operator '{node.op}' cannot be applied to"
                f" '{left_type}' and '{right_type}'",
                node,
            )
        return self._resolve(node, result_type)

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        """Check addressable storage, dereferences, and numeric unary operators."""
        if node.op == "&":
            if isinstance(node.operand, Identifier):
                symbol = self._variable_binding(node.operand)
                self._resolve(node.operand, symbol.type_name)
                if not _is_numeric(symbol.type_name):
                    self._error(
                        "address-of requires an int or bool variable; pointer-to-pointer is excluded",
                        node,
                    )
                symbol.address_taken = True
                return self._resolve(node, symbol.type_name + "*")
            if isinstance(node.operand, UnaryOp) and node.operand.op == "*":
                value_type = self._expression_type(node.operand)
                return self._resolve(node, value_type + "*")
            self._error("address-of requires a variable or dereference", node)
        operand_type = self._expression_type(node.operand, allow_void=True)
        if node.op == "*":
            if not is_pointer(operand_type):
                self._error(
                    f"dereference requires int* or bool*, found '{operand_type}'",
                    node,
                )
            return self._resolve(node, operand_type[:-1])
        if node.op not in ("!", "-"):
            self._error(f"unsupported unary operator '{node.op}'", node)
        if not (
            _is_numeric(operand_type)
            or node.op == "!"
            and is_pointer(operand_type)
        ):
            self._error(
                f"operator '{node.op}' cannot be applied to '{operand_type}'",
                node,
            )
        return self._resolve(node, TYPE_BOOL if node.op == "!" else TYPE_INT)

    def visit_Call(self, node: Call) -> str:
        """Resolve the nearest callee and check its argument list."""
        symbol = self.lookup(node.callee)
        if symbol is None:
            self._error(f"call to undeclared function '{node.callee}'", node)
        if symbol.kind != "function":
            self._error(
                f"cannot call {symbol.kind} '{node.callee}'"
                f" of type '{symbol.type_name}'",
                node,
            )
        if node.callee not in self._visible_functions:
            self._error(
                f"function '{node.callee}' must be declared before it is called",
                node,
            )
        if not symbol.defined:
            self._error(
                f"function '{node.callee}' is declared but not defined", node
            )
        node.binding_id = symbol.binding_id
        if symbol.builtin and node.callee == "printf":
            return self._visit_printf(node)
        if len(node.args) != len(symbol.params):
            self._error(
                f"function '{node.callee}' expects {len(symbol.params)} arguments"
                f" but {len(node.args)} were given",
                node,
            )
        for index, (arg, param) in enumerate(
            zip(node.args, symbol.params), start=1
        ):
            arg_type = self._expression_type(arg)
            if not self._assignable(param.type_name, arg_type, arg):
                self._error(
                    f"function '{node.callee}' argument {index} expects type"
                    f" '{param.type_name}', found '{arg_type}'",
                    arg,
                )
        return self._resolve(node, symbol.type_name)

    def _visit_printf(self, node: Call) -> str:
        """Validate printf with Module 7's helper, or the private fallback."""
        if not node.args:
            self._error(
                "function 'printf' expects at least 1 argument but 0 were given",
                node,
            )
        fmt = node.args[0]
        if not isinstance(fmt, StringLiteral):
            self._error(
                "first argument to 'printf' must be a string literal", fmt
            )
        self._expression_type(fmt)
        arg_types = [self._expression_type(arg) for arg in node.args[1:]]
        try:
            from cminus.extras.format_io import validate_printf
        except ImportError:
            _basic_printf_check(fmt.value, arg_types, node.line, node.column)
        else:
            validate_printf(fmt.value, arg_types, node.line, node.column)
        return self._resolve(node, TYPE_INT)

    def visit_IntLiteral(self, node: IntLiteral) -> str:
        """Annotate an integer literal."""
        return self._resolve(node, TYPE_INT)

    def visit_BoolLiteral(self, node: BoolLiteral) -> str:
        """Annotate a boolean literal."""
        return self._resolve(node, TYPE_BOOL)

    def visit_StringLiteral(self, node: StringLiteral) -> str:
        """Annotate a string literal."""
        return self._resolve(node, TYPE_STRING)


def analyse(program: Program) -> SymbolTable:
    """Check a program and return its complete symbol table."""
    return SemanticAnalyser().analyse(program)
