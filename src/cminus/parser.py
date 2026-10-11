"""Recursive-descent parser for the documented C-Minus core grammar."""

from __future__ import annotations

from cminus import ast_nodes as nodes
from cminus.errors import ParseError
from cminus.lexer_analyser import decode_string
from cminus.tokens import Token


class Parser:
    def __init__(self, tokens: list[Token]):
        if not tokens or tokens[-1].type != "EOF":
            raise ParseError("token stream must end with EOF")
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def location(self, token: Token) -> dict[str, int]:
        return {"line": token.line, "column": token.column}

    def error(self, message: str, token: Token | None = None):
        token = self.current if token is None else token
        raise ParseError(message, token.line, token.column)

    def take(self) -> Token:
        token = self.current
        if token.type != "EOF":
            self.index += 1
        return token

    def match(self, lexeme: str) -> bool:
        if self.current.lexeme == lexeme and self.current.type != "EOF":
            self.take()
            return True
        return False

    def expect(self, lexeme: str) -> Token:
        if self.current.lexeme != lexeme or self.current.type == "EOF":
            found = (
                repr(self.current.lexeme)
                if self.current.type != "EOF"
                else "end of input"
            )
            self.error(f"expected '{lexeme}', found {found}")
        return self.take()

    def declarator_type(self, type_token: Token) -> str:
        """Recognize one pointer level while leaving multiplication to expressions."""
        if not self.match("*"):
            return type_token.lexeme
        if type_token.lexeme == "void":
            self.error(
                "void pointers are outside the supported subset", type_token
            )
        if self.current.lexeme == "*":
            self.error(
                "multiple pointer levels are outside the supported subset"
            )
        return type_token.lexeme + "*"

    def identifier(self) -> Token:
        if self.current.type != "IDENTIFIER":
            self.error("expected an identifier")
        return self.take()

    def type_name(self, *, allow_void: bool = False) -> Token:
        allowed = {"int", "bool", "void"} if allow_void else {"int", "bool"}
        if self.current.lexeme not in allowed:
            self.error(
                "expected a supported type (int, bool"
                + (", void)" if allow_void else ")")
            )
        return self.take()

    def parse(self) -> nodes.Program:
        first = self.current
        includes = []
        while self.current.type == "INCLUDE":
            includes.append(
                self.take().lexeme.split("<", 1)[1].split(">", 1)[0]
            )
        declarations = []
        while self.current.type != "EOF":
            return_type = self.type_name(allow_void=True)
            declared_type = self.declarator_type(return_type)
            name = self.identifier()
            if self.current.lexeme != "(":
                declarations.append(
                    self.finish_declaration(declared_type, name)
                )
                continue
            self.take()
            params = []
            if self.match("void"):
                if self.current.lexeme != ")":
                    self.error("void must be the entire empty parameter list")
            elif self.current.lexeme != ")":
                while True:
                    type_token = self.type_name()
                    param_type = self.declarator_type(type_token)
                    param = (
                        self.take()
                        if self.current.type == "IDENTIFIER"
                        else None
                    )
                    params.append(
                        nodes.Param(
                            param_type,
                            "" if param is None else param.lexeme,
                            **self.location(
                                type_token if param is None else param
                            ),
                        )
                    )
                    if not self.match(","):
                        break
            self.expect(")")
            if self.match(";"):
                declarations.append(
                    nodes.FunctionPrototype(
                        declared_type,
                        name.lexeme,
                        params,
                        **self.location(name),
                    )
                )
                continue
            for param in params:
                if not param.name:
                    raise ParseError(
                        "function definitions require parameter names",
                        param.line,
                        param.column,
                    )
            body = self.block()
            declarations.append(
                nodes.FunctionDecl(
                    declared_type,
                    name.lexeme,
                    params,
                    body,
                    **self.location(name),
                )
            )
        return nodes.Program(declarations, includes, **self.location(first))

    def block(self) -> nodes.Block:
        opening = self.expect("{")
        statements = []
        while self.current.lexeme != "}":
            if self.current.type == "EOF":
                self.error("expected '}' before end of input")
            statements.append(self.statement(allow_declaration=True))
        self.take()
        return nodes.Block(statements, **self.location(opening))

    def declaration(self) -> nodes.VarDecl:
        type_token = self.type_name()
        declared_type = self.declarator_type(type_token)
        name = self.identifier()
        return self.finish_declaration(declared_type, name)

    def finish_declaration(self, type_name: str, name: Token) -> nodes.VarDecl:
        init = self.expression() if self.match("=") else None
        self.expect(";")
        return nodes.VarDecl(
            type_name, name.lexeme, init, **self.location(name)
        )

    def condition(self) -> nodes.Expr:
        self.expect("(")
        value = self.expression()
        self.expect(")")
        return value

    def statement(self, *, allow_declaration: bool = False) -> nodes.Stmt:
        token = self.current
        location = self.location(token)
        if token.lexeme == "{":
            return self.block()
        if self.match(";"):
            return nodes.Block([], **location)
        if token.lexeme in {"int", "bool"}:
            if not allow_declaration:
                self.error("declarations require a block")
            return self.declaration()
        if self.match("if"):
            condition = self.condition()
            then_branch = self.statement()
            else_branch = self.statement() if self.match("else") else None
            return nodes.If(condition, then_branch, else_branch, **location)
        if self.match("while"):
            condition = self.condition()
            return nodes.While(condition, self.statement(), **location)
        if self.match("do"):
            body = self.statement()
            self.expect("while")
            condition = self.condition()
            self.expect(";")
            return nodes.DoWhile(body, condition, **location)
        if self.match("for"):
            self.expect("(")
            if self.match(";"):
                init = None
            elif self.current.lexeme in {"int", "bool"}:
                init = self.declaration()
            else:
                init_expr = self.expression()
                init = nodes.ExprStmt(
                    init_expr, line=init_expr.line, column=init_expr.column
                )
                self.expect(";")
            condition = (
                None if self.current.lexeme == ";" else self.expression()
            )
            self.expect(";")
            step = None if self.current.lexeme == ")" else self.expression()
            self.expect(")")
            return nodes.For(
                init, condition, step, self.statement(), **location
            )
        if self.match("return"):
            value = None if self.current.lexeme == ";" else self.expression()
            self.expect(";")
            return nodes.Return(value, **location)
        if self.match("break"):
            self.expect(";")
            return nodes.Break(**location)
        if self.match("continue"):
            self.expect(";")
            return nodes.Continue(**location)
        if token.type == "KEYWORD":
            self.error(f"'{token.lexeme}' is outside the core")
        value = self.expression()
        self.expect(";")
        return nodes.ExprStmt(value, **location)

    def expression(self) -> nodes.Expr:
        left = self.binary(0)
        if self.current.lexeme == "=":
            operator = self.take()
            if not (
                isinstance(left, nodes.Identifier)
                or isinstance(left, nodes.UnaryOp)
                and left.op == "*"
            ):
                self.error(
                    "assignment target must be a variable or dereference",
                    operator,
                )
            return nodes.Assign(
                left, self.expression(), **self.location(operator)
            )
        return left

    _LEVELS = (
        {"||"},
        {"&&"},
        {"==", "!="},
        {"<", "<=", ">", ">="},
        {"+", "-"},
        {"*", "/", "%"},
    )

    def binary(self, level: int) -> nodes.Expr:
        if level == len(self._LEVELS):
            return self.unary()
        left = self.binary(level + 1)
        while self.current.lexeme in self._LEVELS[level]:
            operator = self.take()
            left = nodes.BinaryOp(
                operator.lexeme,
                left,
                self.binary(level + 1),
                **self.location(operator),
            )
        return left

    def unary(self) -> nodes.Expr:
        if self.current.lexeme in {"-", "!", "&", "*"}:
            operator = self.take()
            return nodes.UnaryOp(
                operator.lexeme, self.unary(), **self.location(operator)
            )
        return self.primary()

    def primary(self) -> nodes.Expr:
        token = self.take()
        location = self.location(token)
        if token.type == "INT":
            return nodes.IntLiteral(int(token.lexeme), **location)
        if token.type == "BOOL":
            return nodes.BoolLiteral(token.lexeme == "true", **location)
        if token.type == "STRING":
            return nodes.StringLiteral(decode_string(token.lexeme), **location)
        if token.type == "IDENTIFIER":
            if not self.match("("):
                return nodes.Identifier(token.lexeme, **location)
            args = []
            if self.current.lexeme != ")":
                while True:
                    args.append(self.expression())
                    if not self.match(","):
                        break
            self.expect(")")
            return nodes.Call(token.lexeme, args, **location)
        if token.lexeme == "(":
            value = self.expression()
            self.expect(")")
            return value
        self.error("expected an expression", token)


def parse(tokens: list[Token]) -> nodes.Program:
    return Parser(tokens).parse()
