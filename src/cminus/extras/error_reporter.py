"""Render a positioned phase error with the original source and a caret."""

from cminus.errors import CMinusError


def render_error(error: CMinusError, filename: str, source: str) -> str:
    header = f"{filename}:{error}"
    lines = source.splitlines()
    if error.line is None or not 1 <= error.line <= len(lines):
        return header
    text = lines[error.line - 1]
    offset = max(0, (error.column or 1) - 1)
    return (
        header
        + "\n"
        + text.expandtabs(8)
        + "\n"
        + " " * len(text[:offset].expandtabs(8))
        + "^"
    )
