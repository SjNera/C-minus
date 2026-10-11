"""The scalar types supported by the C-Minus language."""

NUMERIC_TYPES = {"int", "bool"}
POINTER_TYPES = {"int*", "bool*"}


def is_numeric(type_name: str) -> bool:
    return type_name in NUMERIC_TYPES


def is_pointer(type_name: str) -> bool:
    return type_name in POINTER_TYPES


def is_scalar(type_name: str) -> bool:
    return is_numeric(type_name) or is_pointer(type_name)
