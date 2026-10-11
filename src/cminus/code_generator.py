"""Generate standalone Python from a validated, bound C-Minus AST."""

from __future__ import annotations

import ast
import inspect

from cminus import ast_nodes as nodes, runtime
from cminus.semantic_analyser import SymbolTable


def _name(identifier: str, *, store: bool = False) -> ast.Name:
    return ast.Name(id=identifier, ctx=ast.Store() if store else ast.Load())


def _call(identifier: str, *args: ast.expr) -> ast.Call:
    return ast.Call(func=_name(identifier), args=list(args), keywords=[])


class _RuntimeNames(ast.NodeTransformer):
    mapping = {
        "sys": "_cminus_sys",
        "c_int_div": "_cminus_div",
        "c_int_mod": "_cminus_mod",
        "c_printf": "_cminus_printf",
    }

    def visit_Name(self, node):
        node.id = self.mapping.get(node.id, node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)


class CodeGenerator:
    def __init__(self, symbols: SymbolTable):
        self.symbols = symbols
        self.helpers: set[str] = set()
        self.return_type = "void"

    def bound_name(self, node: nodes.Node) -> str:
        if node.binding_id is None or node.binding_id not in self.symbols.bindings:
            raise ValueError("code generation requires an AST bound by analyse()")
        symbol = self.symbols.bindings[node.binding_id]
        if symbol.builtin:
            return "_cminus_printf"
        if symbol.kind == "function" and symbol.name == "main":
            return "main"
        return f"{symbol.name}__cm{symbol.binding_id}"

    def convert(self, value: ast.expr, type_name: str) -> ast.expr:
        return _call("bool" if type_name == "bool" else "int", value)

    def expression(self, node: nodes.Expr) -> ast.expr:
        if isinstance(node, (nodes.IntLiteral, nodes.BoolLiteral, nodes.StringLiteral)):
            return ast.Constant(value=node.value)
        if isinstance(node, nodes.Identifier):
            return _name(self.bound_name(node))
        if isinstance(node, nodes.Assign):
            return ast.NamedExpr(
                target=_name(self.bound_name(node.target), store=True),
                value=self.convert(
                    self.expression(node.value), node.target.resolved_type
                ),
            )
        if isinstance(node, nodes.Call):
            symbol = self.symbols.bindings[node.binding_id]
            args = [self.expression(arg) for arg in node.args]
            if symbol.builtin:
                self.helpers.add("c_printf")
            else:
                args = [
                    self.convert(arg, param.type_name)
                    for arg, param in zip(args, symbol.params)
                ]
            return _call(self.bound_name(node), *args)
        if isinstance(node, nodes.UnaryOp):
            operand = self.expression(node.operand)
            if node.op == "!":
                return _call("int", ast.UnaryOp(op=ast.Not(), operand=operand))
            return ast.UnaryOp(op=ast.USub(), operand=operand)
        if isinstance(node, nodes.BinaryOp):
            left, right = self.expression(node.left), self.expression(node.right)
            if node.op in {"&&", "||"}:
                value = ast.BoolOp(
                    op=ast.And() if node.op == "&&" else ast.Or(),
                    values=[_call("bool", left), _call("bool", right)],
                )
                return _call("int", value)
            comparisons = {
                "<": ast.Lt,
                "<=": ast.LtE,
                ">": ast.Gt,
                ">=": ast.GtE,
                "==": ast.Eq,
                "!=": ast.NotEq,
            }
            if node.op in comparisons:
                return _call(
                    "int",
                    ast.Compare(
                        left=left, ops=[comparisons[node.op]()], comparators=[right]
                    ),
                )
            if node.op in {"/", "%"}:
                self.helpers.add("c_int_div")
                if node.op == "%":
                    self.helpers.add("c_int_mod")
                return _call(
                    "_cminus_div" if node.op == "/" else "_cminus_mod", left, right
                )
            operators = {"+": ast.Add, "-": ast.Sub, "*": ast.Mult}
            return ast.BinOp(left=left, op=operators[node.op](), right=right)
        raise ValueError(f"unsupported expression {type(node).__name__}")

    def body(self, node: nodes.Stmt) -> list[ast.stmt]:
        return self.statements(node) or [ast.Pass()]

    def statements(self, node: nodes.Stmt) -> list[ast.stmt]:
        if isinstance(node, nodes.Block):
            return [
                statement
                for child in node.statements
                for statement in self.statements(child)
            ]
        if isinstance(node, nodes.VarDecl):
            if node.init is None:
                return []
            return [
                ast.Assign(
                    targets=[_name(self.bound_name(node), store=True)],
                    value=self.convert(self.expression(node.init), node.type_name),
                )
            ]
        if isinstance(node, nodes.ExprStmt):
            if isinstance(node.expr, nodes.Assign):
                value = self.expression(node.expr)
                return [ast.Assign(targets=[value.target], value=value.value)]
            return [ast.Expr(value=self.expression(node.expr))]
        if isinstance(node, nodes.Return):
            value = (
                None
                if node.value is None
                else self.convert(self.expression(node.value), self.return_type)
            )
            return [ast.Return(value=value)]
        if isinstance(node, nodes.If):
            return [
                ast.If(
                    test=self.expression(node.condition),
                    body=self.body(node.then_branch),
                    orelse=(
                        [] if node.else_branch is None else self.body(node.else_branch)
                    ),
                )
            ]
        if isinstance(node, nodes.While):
            return [
                ast.While(
                    test=self.expression(node.condition),
                    body=self.body(node.body),
                    orelse=[],
                )
            ]
        if isinstance(node, nodes.DoWhile):
            body = self.body(node.body)
            body.append(
                ast.If(
                    test=ast.UnaryOp(
                        op=ast.Not(), operand=self.expression(node.condition)
                    ),
                    body=[ast.Break()],
                    orelse=[],
                )
            )
            return [ast.While(test=ast.Constant(value=True), body=body, orelse=[])]
        if isinstance(node, nodes.For):
            initial = [] if node.init is None else self.statements(node.init)
            body = self.body(node.body)
            if node.step is not None:
                body.append(ast.Expr(value=self.expression(node.step)))
            condition = (
                ast.Constant(value=True)
                if node.condition is None
                else self.expression(node.condition)
            )
            return initial + [ast.While(test=condition, body=body, orelse=[])]
        raise ValueError(f"unsupported statement {type(node).__name__}")

    def function(self, node: nodes.FunctionDecl) -> ast.FunctionDef:
        self.return_type = node.return_type
        body = self.statements(node.body)
        if node.name == "main":
            body.append(ast.Return(value=ast.Constant(value=0)))
        arguments = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=self.bound_name(param)) for param in node.params],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        kwargs = {"type_params": []} if "type_params" in ast.FunctionDef._fields else {}
        return ast.FunctionDef(
            name=self.bound_name(node),
            args=arguments,
            body=body or [ast.Pass()],
            decorator_list=[],
            returns=None,
            type_comment=None,
            **kwargs,
        )

    def generate(self, program: nodes.Program) -> str:
        functions = [self.function(function) for function in program.functions]
        helpers = []
        for helper in ("c_int_div", "c_int_mod", "c_printf"):
            if helper in self.helpers:
                definition = ast.parse(
                    inspect.getsource(getattr(runtime, helper))
                ).body[0]
                helpers.append(_RuntimeNames().visit(definition))
        entry = ast.parse(
            'if __name__ == "__main__":\n    raise SystemExit(main())'
        ).body
        module = ast.Module(
            body=[
                ast.Import(names=[ast.alias(name="sys", asname="_cminus_sys")]),
                *helpers,
                *functions,
                *entry,
            ],
            type_ignores=[],
        )
        ast.fix_missing_locations(module)
        compile(module, "<generated>", "exec")
        source = (
            "# Generated by C-Minus; standalone Python 3.10+.\n"
            + ast.unparse(module)
            + "\n"
        )
        ast.parse(source, feature_version=(3, 10))
        compile(source, "<generated>", "exec")
        return source


def generate(program: nodes.Program, symbols: SymbolTable) -> str:
    return CodeGenerator(symbols).generate(program)
