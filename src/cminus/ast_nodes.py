"""Shared AST node definitions (owner: Module 2 - Parser).

Types are plain strings: "int", "bool", "string", "void".

Every node carries `line` and `column` (keyword-only, default 0).
Every Expr carries `resolved_type`, which the semantic analyser fills in and the
code generator reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

TYPE_INT = "int"
TYPE_BOOL = "bool"
TYPE_STRING = "string"
TYPE_VOID = "void"


@dataclass
class Node:
    line: int = field(default=0, kw_only=True)
    column: int = field(default=0, kw_only=True)
    binding_id: Optional[int] = field(default=None, kw_only=True)


# ------------------------------------------------------------------ expressions
@dataclass
class Expr(Node):
    resolved_type: Optional[str] = field(default=None, kw_only=True)


@dataclass
class IntLiteral(Expr):
    value: int


@dataclass
class BoolLiteral(Expr):
    value: bool


@dataclass
class StringLiteral(Expr):
    value: (
        str  # decoded contents between the quotes (e.g. "\n" is already a newline char)
    )


@dataclass
class Identifier(Expr):
    name: str


@dataclass
class Assign(Expr):
    target: Identifier
    value: Expr


@dataclass
class BinaryOp(Expr):
    op: str  # + - * / % < <= > >= == != && ||
    left: Expr
    right: Expr


@dataclass
class UnaryOp(Expr):
    op: str  # ! -
    operand: Expr


@dataclass
class Call(Expr):
    callee: str
    args: list[Expr] = field(default_factory=list)


# ------------------------------------------------------------------- statements
@dataclass
class Stmt(Node):
    pass


@dataclass
class VarDecl(Stmt):
    type_name: str
    name: str
    init: Optional[Expr] = None


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class Block(Stmt):
    statements: list[Stmt] = field(default_factory=list)


@dataclass
class If(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] = None


@dataclass
class While(Stmt):
    condition: Expr
    body: Stmt


@dataclass
class DoWhile(Stmt):
    body: Stmt
    condition: Expr


@dataclass
class For(Stmt):
    init: Optional[Stmt]  # VarDecl or ExprStmt or None
    condition: Optional[Expr]
    step: Optional[Expr]
    body: Stmt


@dataclass
class Return(Stmt):
    value: Optional[Expr] = None


@dataclass
class Break(Stmt):
    pass


@dataclass
class Continue(Stmt):
    pass


# ------------------------------------------------------------------ top level
@dataclass
class Param(Node):
    type_name: str
    name: str


@dataclass
class FunctionDecl(Node):
    return_type: str
    name: str
    params: list[Param]
    body: Block


@dataclass
class FunctionPrototype(Node):
    return_type: str
    name: str
    params: list[Param]


@dataclass
class Program(Node):
    declarations: list[FunctionDecl | FunctionPrototype | VarDecl]
    includes: list[str] = field(default_factory=list)  # e.g. ["stdio.h"]

    @property
    def functions(self) -> list[FunctionDecl]:
        return [node for node in self.declarations if isinstance(node, FunctionDecl)]

    @property
    def globals(self) -> list[VarDecl]:
        return [node for node in self.declarations if isinstance(node, VarDecl)]
