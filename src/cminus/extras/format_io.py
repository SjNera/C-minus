"""Compile-time checking of the core printf format language."""

from cminus.errors import SemanticError


def validate_printf(fmt: str, arg_types: list[str], line: int, column: int) -> None:
    specifiers = []
    index = 0
    fmt = fmt.split("\0", 1)[0]
    while index < len(fmt):
        if fmt[index] != "%":
            index += 1
            continue
        index += 1
        if index == len(fmt):
            raise SemanticError("incomplete printf format specifier '%'", line, column)
        specifier = fmt[index]
        index += 1
        if specifier == "%":
            continue
        if specifier not in {"d", "i", "c", "s"}:
            raise SemanticError(
                f"unsupported printf format specifier '%{specifier}'", line, column
            )
        specifiers.append(specifier)
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
            raise SemanticError(
                f"printf specifier '%{specifier}' expects {expected}, found '{type_name}'",
                line,
                column,
            )
