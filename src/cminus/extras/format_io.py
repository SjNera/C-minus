"""Compile-time checking of the core printf format language."""

from cminus.errors import SemanticError
from cminus.runtime import parse_printf_format


def validate_printf(fmt: str, arg_types: list[str], line: int, column: int) -> None:
    try:
        parts = parse_printf_format(fmt)
    except ValueError as error:
        raise SemanticError(str(error), line, column) from error
    specifiers = []
    for part in parts:
        if isinstance(part, str):
            continue
        _, width, precision, conversion = part
        if width == "*":
            specifiers.append("field width")
        if precision == "*":
            specifiers.append("precision")
        specifiers.append(conversion)
    if len(specifiers) != len(arg_types):
        raise SemanticError(
            f"printf format expects {len(specifiers)} arguments but {len(arg_types)} were given",
            line,
            column,
        )
    for specifier, type_name in zip(specifiers, arg_types):
        valid = (
            type_name == "string" if specifier == "s" else type_name in {"int", "bool"}
        )
        if not valid:
            expected = "'string'" if specifier == "s" else "int or bool"
            label = (
                f"specifier '%{specifier}'"
                if specifier in {"d", "i", "s", "c"}
                else specifier
            )
            raise SemanticError(
                f"printf {label} expects {expected}, found '{type_name}'",
                line,
                column,
            )
