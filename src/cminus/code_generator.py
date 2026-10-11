"""Generate standalone Python from a validated, bound C-Minus AST."""

from __future__ import annotations

import ast
from dataclasses import fields
import inspect

from cminus import ast_nodes as nodes, runtime
from cminus.printf_generator import print_statement, simple_text
from cminus.python_names import readable_names
from cminus.semantic_analyser import SymbolTable, is_null_constant
from cminus.types import is_pointer


def _name(identifier: str, *, store: bool = False) -> ast.Name:
    return ast.Name(id=identifier, ctx=ast.Store() if store else ast.Load())


def _call(identifier: str, *args: ast.expr) -> ast.Call:
    return ast.Call(func=_name(identifier), args=list(args), keywords=[])


def _uses_binding(node: nodes.Node, binding_id: int) -> bool:
    if node.binding_id == binding_id:
        return True
    for field in fields(node):
        value = getattr(node, field.name)
        children = value if isinstance(value, list) else [value]
        if any(
            isinstance(child, nodes.Node) and _uses_binding(child, binding_id)
            for child in children
        ):
            return True
    return False


class _RuntimeNames(ast.NodeTransformer):
    mapping = {
        "c_int_div": "c_div",
        "c_int_mod": "c_mod",
        "c_printf_parts": "printf",
        "write_text": "write",
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
        self.names = readable_names(symbols)
        self.helpers: set[str] = set()
        self.return_type = "void"
        self.loops: list[nodes.While | nodes.DoWhile | nodes.For] = []
        self.global_writes: set[str] = set()
        self.print_output = False

    def bound_name(self, node: nodes.Node) -> str:
        if (
            node.binding_id is None
            or node.binding_id not in self.symbols.bindings
        ):
            raise ValueError(
                "code generation requires an AST bound by analyse()"
            )
        return self.names[node.binding_id]

    def convert(self, node: nodes.Expr, type_name: str) -> ast.expr:
        value = self.expression(node)
        if is_pointer(type_name):
            return (
                ast.Constant(value=None) if is_null_constant(node) else value
            )
        if type_name == node.resolved_type:
            return value
        if isinstance(value, ast.Constant):
            return ast.Constant(
                value=(
                    bool(value.value)
                    if type_name == "bool"
                    else int(value.value)
                )
            )
        return _call("bool" if type_name == "bool" else "int", value)

    def target(self, node: nodes.Expr) -> ast.expr:
        """Keep direct assignments readable, including stores through pointers."""
        if isinstance(node, nodes.Identifier):
            symbol = self.symbols.bindings[node.binding_id]
            if symbol.address_taken:
                return ast.Attribute(
                    value=_name(self.bound_name(node)),
                    attr="value",
                    ctx=ast.Store(),
                )
            if symbol.is_global:
                self.global_writes.add(self.bound_name(node))
            return _name(self.bound_name(node), store=True)
        return ast.Attribute(
            value=self.expression(node.operand), attr="value", ctx=ast.Store()
        )

    def condition(self, node: nodes.Expr) -> ast.expr:
        if isinstance(node, nodes.BinaryOp) and node.op in {"&&", "||"}:
            return ast.BoolOp(
                op=ast.And() if node.op == "&&" else ast.Or(),
                values=[self.condition(node.left), self.condition(node.right)],
            )
        if isinstance(node, nodes.UnaryOp) and node.op == "!":
            return ast.UnaryOp(
                op=ast.Not(), operand=self.condition(node.operand)
            )
        return self.expression(node)

    def expression(self, node: nodes.Expr) -> ast.expr:
        if isinstance(
            node, (nodes.IntLiteral, nodes.BoolLiteral, nodes.StringLiteral)
        ):
            return ast.Constant(value=node.value)
        if isinstance(node, nodes.Identifier):
            value = _name(self.bound_name(node))
            if self.symbols.bindings[node.binding_id].address_taken:
                return ast.Attribute(value=value, attr="value", ctx=ast.Load())
            return value
        if isinstance(node, nodes.Assign):
            target = self.target(node.target)
            value = self.convert(node.value, node.target.resolved_type)
            if isinstance(target, ast.Attribute):
                self.helpers.add("set_value")
                return _call("set_value", target.value, value)
            return ast.NamedExpr(
                target=target,
                value=value,
            )
        if isinstance(node, nodes.Call):
            symbol = self.symbols.bindings[node.binding_id]
            if symbol.builtin:
                text = simple_text(node, self.expression)
                if text is not None:
                    self.helpers.add("write_text")
                    return _call("write", text)
                self.helpers.add("c_printf_parts")
                parts = ast.parse(
                    repr(runtime.parse_printf_format(node.args[0].value)),
                    mode="eval",
                ).body
                return _call(
                    "printf",
                    parts,
                    *(self.expression(arg) for arg in node.args[1:]),
                )
            args = [
                self.convert(arg, param.type_name)
                for arg, param in zip(node.args, symbol.params)
            ]
            return _call(self.bound_name(node), *args)
        if isinstance(node, nodes.UnaryOp):
            if node.op == "&":
                if isinstance(node.operand, nodes.Identifier):
                    return _name(self.bound_name(node.operand))
                return self.expression(node.operand.operand)
            operand = self.expression(node.operand)
            if node.op == "*":
                return ast.Attribute(
                    value=operand, attr="value", ctx=ast.Load()
                )
            if node.op == "!":
                return ast.UnaryOp(op=ast.Not(), operand=operand)
            return ast.UnaryOp(op=ast.USub(), operand=operand)
        if isinstance(node, nodes.BinaryOp):
            left, right = self.expression(node.left), self.expression(
                node.right
            )
            if node.op in {"&&", "||"}:
                return _call("bool", self.condition(node))
            comparisons = {
                "<": ast.Lt,
                "<=": ast.LtE,
                ">": ast.Gt,
                ">=": ast.GtE,
                "==": ast.Eq,
                "!=": ast.NotEq,
            }
            if node.op in comparisons:
                operator = comparisons[node.op]()
                if is_pointer(node.left.resolved_type) or is_pointer(
                    node.right.resolved_type
                ):
                    left = (
                        ast.Constant(value=None)
                        if is_null_constant(node.left)
                        else left
                    )
                    right = (
                        ast.Constant(value=None)
                        if is_null_constant(node.right)
                        else right
                    )
                    operator = ast.Is() if node.op == "==" else ast.IsNot()
                return ast.Compare(
                    left=left, ops=[operator], comparators=[right]
                )
            if node.op in {"/", "%"}:
                self.helpers.add("c_int_div")
                if node.op == "%":
                    self.helpers.add("c_int_mod")
                return _call(
                    "c_div" if node.op == "/" else "c_mod", left, right
                )
            operators = {"+": ast.Add, "-": ast.Sub, "*": ast.Mult}
            return ast.BinOp(left=left, op=operators[node.op](), right=right)
        raise ValueError(f"unsupported expression {type(node).__name__}")

    def body(self, node: nodes.Stmt) -> list[ast.stmt]:
        return self.statements(node) or [ast.Pass()]

    def loop_body(
        self, node: nodes.While | nodes.DoWhile | nodes.For
    ) -> list[ast.stmt]:
        self.loops.append(node)
        try:
            return self.body(node.body)
        finally:
            self.loops.pop()

    def exit_if_false(self, condition: nodes.Expr) -> ast.If:
        return ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=self.condition(condition)),
            body=[ast.Break()],
            orelse=[],
        )

    def statements(self, node: nodes.Stmt) -> list[ast.stmt]:
        if isinstance(node, nodes.Block):
            return [
                statement
                for child in node.statements
                for statement in self.statements(child)
            ]
        if isinstance(node, nodes.VarDecl):
            symbol = self.symbols.bindings[node.binding_id]
            if node.init is None and not symbol.address_taken:
                return []
            value = (
                ast.Constant(value=None)
                if node.init is None
                else self.convert(node.init, node.type_name)
            )
            if symbol.address_taken:
                self.helpers.add("Reference")
                if node.init is not None and _uses_binding(
                    node.init, node.binding_id
                ):
                    name = self.bound_name(node)
                    return [
                        ast.Assign(
                            targets=[_name(name, store=True)],
                            value=_call("Reference", ast.Constant(value=None)),
                        ),
                        ast.Assign(
                            targets=[
                                ast.Attribute(
                                    value=_name(name),
                                    attr="value",
                                    ctx=ast.Store(),
                                )
                            ],
                            value=value,
                        ),
                    ]
                value = _call("Reference", value)
            return [
                ast.Assign(
                    targets=[_name(self.bound_name(node), store=True)],
                    value=value,
                )
            ]
        if isinstance(node, nodes.ExprStmt):
            if isinstance(node.expr, nodes.Assign):
                target = self.target(node.expr.target)
                value = self.convert(
                    node.expr.value, node.expr.target.resolved_type
                )
                return [ast.Assign(targets=[target], value=value)]
            if (
                isinstance(node.expr, nodes.Call)
                and self.symbols.bindings[node.expr.binding_id].builtin
            ):
                text = simple_text(node.expr, self.expression)
                if text is not None:
                    self.print_output = True
                    return [print_statement(text)]
            return [ast.Expr(value=self.expression(node.expr))]
        if isinstance(node, nodes.Return):
            value = (
                None
                if node.value is None
                else self.convert(node.value, self.return_type)
            )
            return [ast.Return(value=value)]
        if isinstance(node, (nodes.Break, nodes.Continue)):
            if not self.loops:
                raise ValueError(
                    "loop jumps require an AST validated by analyse()"
                )
            if isinstance(node, nodes.Break):
                return [ast.Break()]
            loop = self.loops[-1]
            # A Python continue skips the lowered loop's tail. Emit the C
            # continuation operation first, then skip the remaining body.
            if isinstance(loop, nodes.For) and loop.step is not None:
                return self.statements(nodes.ExprStmt(loop.step)) + [
                    ast.Continue()
                ]
            if isinstance(loop, nodes.DoWhile):
                return [self.exit_if_false(loop.condition), ast.Continue()]
            return [ast.Continue()]
        if isinstance(node, nodes.If):
            return [
                ast.If(
                    test=self.condition(node.condition),
                    body=self.body(node.then_branch),
                    orelse=(
                        []
                        if node.else_branch is None
                        else self.body(node.else_branch)
                    ),
                )
            ]
        if isinstance(node, nodes.While):
            return [
                ast.While(
                    test=self.condition(node.condition),
                    body=self.loop_body(node),
                    orelse=[],
                )
            ]
        if isinstance(node, nodes.DoWhile):
            body = self.loop_body(node)
            body.append(self.exit_if_false(node.condition))
            return [
                ast.While(test=ast.Constant(value=True), body=body, orelse=[])
            ]
        if isinstance(node, nodes.For):
            initial = [] if node.init is None else self.statements(node.init)
            body = self.loop_body(node)
            if node.step is not None:
                body.extend(self.statements(nodes.ExprStmt(node.step)))
            condition = (
                ast.Constant(value=True)
                if node.condition is None
                else self.condition(node.condition)
            )
            return initial + [ast.While(test=condition, body=body, orelse=[])]
        raise ValueError(f"unsupported statement {type(node).__name__}")

    def function(self, node: nodes.FunctionDecl) -> ast.FunctionDef:
        self.return_type = node.return_type
        self.global_writes = set()
        body = self.statements(node.body)
        for param in reversed(node.params):
            if self.symbols.bindings[param.binding_id].address_taken:
                self.helpers.add("Reference")
                body.insert(
                    0,
                    ast.Assign(
                        targets=[_name(self.bound_name(param), store=True)],
                        value=_call(
                            "Reference", _name(self.bound_name(param))
                        ),
                    ),
                )
        if self.global_writes:
            body = [
                ast.Global(names=[name]) for name in sorted(self.global_writes)
            ] + body
        if node.name == "main" and (
            not body or not isinstance(body[-1], ast.Return)
        ):
            body.append(ast.Return(value=ast.Constant(value=0)))
        arguments = ast.arguments(
            posonlyargs=[],
            args=[
                ast.arg(arg=self.bound_name(param)) for param in node.params
            ],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        kwargs = (
            {"type_params": []}
            if "type_params" in ast.FunctionDef._fields
            else {}
        )
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
        globals = []
        for node in program.globals:
            symbol = self.symbols.bindings[node.binding_id]
            value = ast.Constant(value=symbol.initial_value)
            if symbol.initial_target is not None:
                value = _name(self.names[symbol.initial_target])
            if symbol.address_taken:
                self.helpers.add("Reference")
                value = _call("Reference", value)
            globals.append(
                ast.Assign(
                    targets=[_name(self.bound_name(node), store=True)],
                    value=value,
                )
            )
        functions = [self.function(function) for function in program.functions]
        helpers = []
        for helper in (
            "Reference",
            "set_value",
            "c_int_div",
            "c_int_mod",
            "write_text",
            "c_printf_parts",
        ):
            if helper in self.helpers:
                definition = ast.parse(
                    inspect.getsource(getattr(runtime, helper))
                ).body[0]
                helpers.append(_RuntimeNames().visit(definition))
        entry = ast.parse(
            'if __name__ == "__main__":\n    raise SystemExit(main())'
        ).body
        prelude = []
        if self.print_output or self.helpers & {
            "write_text",
            "c_printf_parts",
        }:
            prelude.append(ast.Import(names=[ast.alias(name="sys")]))
        if self.print_output:
            prelude.extend(
                ast.parse(
                    'sys.stdout.reconfigure(encoding="utf-8", newline="")'
                ).body
            )
        module = ast.Module(
            body=[
                *prelude,
                *helpers,
                *globals,
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
