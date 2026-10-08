import ast


class CodeGenerator:
    """Walks a validated Abstract Syntax Tree (AST) and emits executable Python 3 code,

    handling indentation levels, dynamic scoping, and C-to-Python operator mappings.
    """

    def __init__(self, indent_size: int = 4):
        self.indent_size = indent_size
        self.indent_level = 0

    def generate(self, node: dict) -> str:
        """Main entry point to generate code for a given AST node."""
        method_name = f"visit_{node.get('type')}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def _indent() -> str:
        return " " * (self.indent_level * self.indent_size)

    def generic_visit(self, node: dict) -> str:
        raise NotImplementedError(
            f"No visitor method defined for node type: {node.get('type')}"
        )

    # -------------------------------------------------------------------------
    # Program & Scoping Structure
    # -------------------------------------------------------------------------

    def visit_Program(self, node: dict) -> str:
        """Generates code for the top-level Program node."""
        statements = []
        for stmt in node.get("body", []):
            code = self.generate(stmt)
            if code.strip():
                statements.append(code)
        return "\n\n".join(statements) + "\n"

    def visit_Block(self, node: dict) -> str:
        """Generates code for a statement block, managing Python indentation."""
        statements = node.get("body", [])
        if not statements:
            return f"{self._indent()}pass"

        lines = []
        for stmt in statements:
            code = self.generate(stmt)
            if code.strip():
                lines.append(code)

        return "\n".join(lines) if lines else f"{self._indent()}pass"

    # -------------------------------------------------------------------------
    # Function & Variable Declarations
    # -------------------------------------------------------------------------

    def visit_FunctionDecl(self, node: dict) -> str:
        """Converts a C function declaration to a Python 'def' function."""
        func_name = node.get("name")
        params = [p.get("name") for p in node.get("params", [])]
        param_str = ", ".join(params)

        header = f"{self._indent()}def {func_name}({param_str}):"

        self.indent_level += 1
        body_code = self.generate(node.get("body"))
        self.indent_level -= 1

        return f"{header}\n{body_code}"

    def visit_VarDecl(self, node: dict) -> str:
        """Translates static variable declarations (e.g., 'int x = 5;') to Python

        assignments ('x = 5').
        """
        var_name = node.get("name")
        init_val = node.get("init")

        if init_val is not None:
            value_code = self.generate(init_val)
            return f"{self._indent()}{var_name} = {value_code}"

        # If declared without initialization, assign None to ensure symbol existence
        return f"{self._indent()}{var_name} = None"

    # -------------------------------------------------------------------------
    # Control Flow
    # -------------------------------------------------------------------------

    def visit_IfStatement(self, node: dict) -> str:
        """Translates if / else statement trees."""
        condition = self.generate(node.get("test"))
        if_line = f"{self._indent()}if {condition}:"

        self.indent_level += 1
        consequent = self.generate(node.get("consequent"))
        self.indent_level -= 1

        result = f"{if_line}\n{consequent}"

        alternate = node.get("alternate")
        if alternate:
            if alternate.get("type") == "IfStatement":
                # Translate 'else if' to 'elif'
                elif_code = self.generate(alternate).lstrip()
                result += f"\nelif {elif_code}"
            else:
                else_line = f"\n{self._indent()}else:"
                self.indent_level += 1
                alt_code = self.generate(alternate)
                self.indent_level -= 1
                result += f"{else_line}\n{alt_code}"

        return result

    def visit_WhileStatement(self, node: dict) -> str:
        """Translates while loops."""
        condition = self.generate(node.get("test"))
        header = f"{self._indent()}while {condition}:"

        self.indent_level += 1
        body = self.generate(node.get("body"))
        self.indent_level -= 1

        return f"{header}\n{body}"

    def visit_ReturnStatement(self, node: dict) -> str:
        """Translates return statements."""
        value = node.get("value")
        if value:
            return f"{self._indent()}return {self.generate(value)}"
        return f"{self._indent()}return"

    def visit_ExpressionStatement(self, node: dict) -> str:
        """Wraps standalone expressions as statements."""
        expr_code = self.generate(node.get("expression"))
        return f"{self._indent()}{expr_code}"

    # -------------------------------------------------------------------------
    # Expressions & Literals
    # -------------------------------------------------------------------------

    def visit_BinaryExpression(self, node: dict) -> str:
        """Converts binary operations, mapping C logical operators to Python words."""
        op_map = {
            "&&": "and",
            "||": "or",
            "!=": "!=",
            "==": "==",
        }

        raw_op = node.get("operator")
        op = op_map.get(raw_op, raw_op)

        left = self.generate(node.get("left"))
        right = self.generate(node.get("right"))

        return f"({left} {op} {right})"

    def visit_AssignmentExpression(self, node: dict) -> str:
        """Handles variable assignments and compound assignments."""
        target = self.generate(node.get("left"))
        op = node.get("operator")  # =, +=, -=, etc.
        value = self.generate(node.get("right"))

        return f"{target} {op} {value}"

    def visit_CallExpression(self, node: dict) -> str:
        """Translates function calls (e.g. printf -> print)."""
        callee = node.get("callee", {}).get("name")

        # Basic built-in mapping
        if callee == "printf":
            callee = "print"

        args = [self.generate(arg) for arg in node.get("arguments", [])]
        return f"{callee}({', '.join(args)})"

    def visit_Identifier(self, node: dict) -> str:
        return node.get("name")

    def visit_Literal(self, node: dict) -> str:
        value = node.get("value")
        if isinstance(value, str):
            return repr(value)
        return str(value)


# -----------------------------------------------------------------------------
# Example Usage & Verification
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example AST representing a C function:
    # int calculate(int x) {
    #     int result = 0;
    #     if (x > 0) {
    #         result = x * 2;
    #     } else {
    #         result = 0;
    #     }
    #     return result;
    # }
    sample_ast = {
        "type": "Program",
        "body": [
            {
                "type": "FunctionDecl",
                "name": "calculate",
                "params": [{"type": "Identifier", "name": "x"}],
                "body": {
                    "type": "Block",
                    "body": [
                        {
                            "type": "VarDecl",
                            "name": "result",
                            "init": {"type": "Literal", "value": 0},
                        },
                        {
                            "type": "IfStatement",
                            "test": {
                                "type": "BinaryExpression",
                                "operator": ">",
                                "left": {"type": "Identifier", "name": "x"},
                                "right": {"type": "Literal", "value": 0},
                            },
                            "consequent": {
                                "type": "Block",
                                "body": [
                                    {
                                        "type": "ExpressionStatement",
                                        "expression": {
                                            "type": "AssignmentExpression",
                                            "operator": "=",
                                            "left": {
                                                "type": "Identifier",
                                                "name": "result",
                                            },
                                            "right": {
                                                "type": "BinaryExpression",
                                                "operator": "*",
                                                "left": {
                                                    "type": "Identifier",
                                                    "name": "x",
                                                },
                                                "right": {
                                                    "type": "Literal",
                                                    "value": 2,
                                                },
                                            },
                                        },
                                    }
                                ],
                            },
                            "alternate": {
                                "type": "Block",
                                "body": [
                                    {
                                        "type": "ExpressionStatement",
                                        "expression": {
                                            "type": "AssignmentExpression",
                                            "operator": "=",
                                            "left": {
                                                "type": "Identifier",
                                                "name": "result",
                                            },
                                            "right": {
                                                "type": "Literal",
                                                "value": 0,
                                            },
                                        },
                                    }
                                ],
                            },
                        },
                        {
                            "type": "ReturnStatement",
                            "value": {"type": "Identifier", "name": "result"},
                        },
                    ],
                },
            }
        ],
    }

    generator = CodeGenerator()
    python_code = generator.generate(sample_ast)

    print("--- Generated Python Code ---")
    print(python_code)

    # Verify that the emitted Python code is syntactically valid
    compiled_ast = ast.parse(python_code)
    print("--- Status: Valid Python 3 Code Generated Successfully ---")
