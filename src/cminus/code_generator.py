"""Module 4 - Code Generator. Owner: Malim Ban.

Translates a validated C-like AST (defined in ast_nodes.py) into executable Python 3 code.
"""

from __future__ import annotations

import ast
from typing import Optional

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
    Program,
    Return,
    Stmt,
    StringLiteral,
    UnaryOp,
    VarDecl,
    While,
)


class CodeGenerator:
    """Translates a C-like AST into Python AST, then emits valid Python 3 source code."""

    def __init__(self, symbols=None):
        self.symbols = symbols

    def generate(self, program: Program) -> str:
        """Main entry point. Converts the Program node to Python source string."""
        py_ast_module = self.visit_Program(program)
        ast.fix_missing_locations(py_ast_module)
        return ast.unparse(py_ast_module)


    def visit(self, node: Optional[Node]):
        if node is None:
            return None
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node):
        raise NotImplementedError(
            f"No visitor method defined for node type: {node.__class__.__name__}"
        )


    def visit_Program(self, node: Program) -> ast.Module:
        body = [self.visit(func) for func in node.functions]
        return ast.Module(body=body, type_ignores=[])

    def visit_FunctionDecl(self, node: FunctionDecl) -> ast.FunctionDef:
        args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=param.name) for param in node.params],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        )
        body = self.visit_Block_body(node.body)
        return ast.FunctionDef(
            name=node.name,
            args=args,
            body=body,
            decorator_list=[],
            returns=None,
        )


    def visit_Block_body(self, block: Block) -> list[ast.stmt]:
        """Helper to process statements inside a block. Ensures non-empty body (pass)."""
        stmts = []
        for stmt in block.statements:
            py_stmt = self.visit(stmt)
            if isinstance(py_stmt, list):
                stmts.extend(py_stmt)
            elif py_stmt is not None:
                stmts.append(py_stmt)

        if not stmts:
            stmts.append(ast.Pass())
        return stmts

    def visit_Block(self, node: Block) -> list[ast.stmt]:
        return self.visit_Block_body(node)

    def visit_VarDecl(self, node: VarDecl) -> ast.Assign:
        target = ast.Name(id=node.name, ctx=ast.Store())
        if node.init is not None:
            value = self.visit(node.init)
        else:
            value = ast.Constant(value=None)
        return ast.Assign(targets=[target], value=value)

    def visit_ExprStmt(self, node: ExprStmt) -> ast.Expr:
        return ast.Expr(value=self.visit(node.expr))

    def visit_If(self, node: If) -> ast.If:
        test = self.visit(node.condition)
        body = (
            self.visit_Block_body(node.then_branch)
            if isinstance(node.then_branch, Block)
            else [self.visit(node.then_branch)]
        )

        orelse = []
        if node.else_branch:
            if isinstance(node.else_branch, Block):
                orelse = self.visit_Block_body(node.else_branch)
            else:
                orelse = [self.visit(node.else_branch)]

        return ast.If(test=test, body=body, orelse=orelse)

    def visit_While(self, node: While) -> ast.While:
        test = self.visit(node.condition)
        body = (
            self.visit_Block_body(node.body)
            if isinstance(node.body, Block)
            else [self.visit(node.body)]
        )
        return ast.While(test=test, body=body, orelse=[])

    def visit_DoWhile(self, node: DoWhile) -> list[ast.stmt]:
        """Translates `do { body } while(cond);` into `while True: body; if not cond: break`."""
        body = (
            self.visit_Block_body(node.body)
            if isinstance(node.body, Block)
            else [self.visit(node.body)]
        )
        
        cond_check = ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=self.visit(node.condition)),
            body=[ast.Break()],
            orelse=[],
        )
        body.append(cond_check)

        return [ast.While(test=ast.Constant(value=True), body=body, orelse=[])]

    def visit_For(self, node: For) -> list[ast.stmt]:
        """Translates C-style `for(init; cond; step)` into Python initialization + while loop."""
        statements = []

        if node.init:
            py_init = self.visit(node.init)
            if isinstance(py_init, list):
                statements.extend(py_init)
            else:
                statements.append(py_init)

        test = self.visit(node.condition) if node.condition else ast.Constant(value=True)

        body = (
            self.visit_Block_body(node.body)
            if isinstance(node.body, Block)
            else [self.visit(node.body)]
        )

        if node.step:
            body.append(ast.Expr(value=self.visit(node.step)))

        while_loop = ast.While(test=test, body=body, orelse=[])
        statements.append(while_loop)

        return statements

    def visit_Return(self, node: Return) -> ast.Return:
        value = self.visit(node.value) if node.value else None
        return ast.Return(value=value)

    
    def visit_Assign(self, node: Assign) -> ast.Assign:
        target = ast.Name(id=node.target.name, ctx=ast.Store())
        value = self.visit(node.value)
        return ast.Assign(targets=[target], value=value)

    def visit_BinaryOp(self, node: BinaryOp) -> ast.AST:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

        if op == "&&":
            return ast.BoolOp(op=ast.And(), values=[left, right])
        if op == "||":
            return ast.BoolOp(op=ast.Or(), values=[left, right])

        cmp_ops = {
            "==": ast.Eq(),
            "!=": ast.NotEq(),
            "<": ast.Lt(),
            "<=": ast.LtE(),
            ">": ast.Gt(),
            ">=": ast.GtE(),
        }
        if op in cmp_ops:
            return ast.Compare(left=left, ops=[cmp_ops[op]], comparators=[right])

        arith_ops = {
            "+": ast.Add(),
            "-": ast.Sub(),
            "*": ast.Mult(),
            "/": ast.FloorDiv() if node.resolved_type == "int" else ast.Div(),
            "%": ast.Mod(),
        }
        if op in arith_ops:
            return ast.BinOp(left=left, op=arith_ops[op], right=right)

        raise ValueError(f"Unsupported binary operator: {op}")

    def visit_UnaryOp(self, node: UnaryOp) -> ast.UnaryOp:
        operand = self.visit(node.operand)
        if node.op == "!":
            return ast.UnaryOp(op=ast.Not(), operand=operand)
        if node.op == "-":
            return ast.UnaryOp(op=ast.USub(), operand=operand)
        raise ValueError(f"Unsupported unary operator: {node.op}")

    def visit_Call(self, node: Call) -> ast.Call:
        callee_name = node.callee
        
        if callee_name == "printf":
            callee_name = "print"

        func = ast.Name(id=callee_name, ctx=ast.Load())
        args = [self.visit(arg) for arg in node.args]
        return ast.Call(func=func, args=args, keywords=[])


    def visit_Identifier(self, node: Identifier) -> ast.Name:
        return ast.Name(id=node.name, ctx=ast.Load())

    def visit_IntLiteral(self, node: IntLiteral) -> ast.Constant:
        return ast.Constant(value=node.value)

    def visit_BoolLiteral(self, node: BoolLiteral) -> ast.Constant:
        return ast.Constant(value=node.value)

    def visit_StringLiteral(self, node: StringLiteral) -> ast.Constant:
        return ast.Constant(value=node.value)


def generate(program: Program, symbols=None) -> str:
    """Module entrypoint contract function."""
    generator = CodeGenerator(symbols=symbols)
    return generator.generate(program)
