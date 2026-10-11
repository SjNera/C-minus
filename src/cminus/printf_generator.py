"""Lower common literal printf formats directly to Python text expressions."""

import ast

from cminus.ast_nodes import IntLiteral, StringLiteral
from cminus.runtime import parse_printf_format


def simple_text(call, expression):
    """Use f-strings when Python can express the format's exact C output."""
    values = []
    argument = 1

    def literal(text):
        if values and isinstance(values[-1], ast.Constant):
            values[-1].value += text
        elif text:
            values.append(ast.Constant(value=text))

    for part in parse_printf_format(call.args[0].value):
        if isinstance(part, str):
            literal(part)
            continue
        flags, width, precision, conversion = part
        value = call.args[argument]
        if width == "*" or precision == "*":
            return None
        argument += 1
        if conversion == "s" and isinstance(value, StringLiteral):
            data = value.value.split("\0", 1)[0].encode("utf-8")
            if precision is not None:
                data = data[:precision]
            padding = b" " * max(0, (width or 0) - len(data))
            data = data + padding if "-" in flags else padding + data
            try:
                literal(data.decode("utf-8"))
            except UnicodeDecodeError:
                return None
        elif (
            conversion == "c"
            and isinstance(value, IntLiteral)
            and value.value % 256 < 128
        ):
            text = chr(value.value % 256)
            literal(
                text.ljust(width or 0)
                if "-" in flags
                else text.rjust(width or 0)
            )
        elif conversion in {"d", "i"} and precision is None:
            sign = "+" if "+" in flags else " " if " " in flags else ""
            if "-" in flags:
                specifier = "<" + sign
            else:
                specifier = sign + ("0" if "0" in flags else "")
            specifier += (str(width) if width else "") + "d"
            values.append(
                ast.FormattedValue(
                    value=expression(value),
                    conversion=-1,
                    format_spec=ast.JoinedStr(
                        values=[ast.Constant(value=specifier)]
                    ),
                )
            )
        else:
            return None
    if not values:
        return ast.Constant(value="")
    if all(isinstance(value, ast.Constant) for value in values):
        return ast.Constant(value="".join(value.value for value in values))
    joined = ast.JoinedStr(values=values)
    if len(ast.unparse(joined)) <= 60:
        return joined
    # Calls and ordinary literals can wrap on Python 3.10; a long f-string
    # cannot always wrap its expression safely on that target version.
    pieces = [
        (
            value
            if isinstance(value, ast.Constant)
            else ast.Call(
                func=ast.Name(id="format", ctx=ast.Load()),
                args=[value.value, value.format_spec.values[0]],
                keywords=[],
            )
        )
        for value in values
    ]
    result = pieces[0]
    for piece in pieces[1:]:
        result = ast.BinOp(left=result, op=ast.Add(), right=piece)
    return result


def print_statement(text):
    """Remove one known trailing newline so ordinary print supplies it."""
    ending = (
        text
        if isinstance(text, ast.Constant)
        else text.values[-1] if isinstance(text, ast.JoinedStr) else None
    )
    newline = isinstance(ending, ast.Constant) and ending.value.endswith("\n")
    if newline:
        ending.value = ending.value[:-1]
    keywords = (
        []
        if newline
        else [ast.keyword(arg="end", value=ast.Constant(value=""))]
    )
    keywords.append(ast.keyword(arg="flush", value=ast.Constant(value=True)))
    return ast.Expr(
        value=ast.Call(
            func=ast.Name(id="print", ctx=ast.Load()),
            args=[text],
            keywords=keywords,
        )
    )
