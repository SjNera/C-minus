"""Format generated Python without changing its parsed meaning."""

import ast
import io
import tokenize

import black

from cminus.errors import CMinusError


class FormattingError(CMinusError):
    kind = "formatting error"


def _split_long_literals(source: str) -> str:
    """Use adjacent literals to wrap long strings without adding runtime work."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    replacements = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING or token.start[0] != token.end[0]:
            continue
        if len(lines[token.start[0] - 1].rstrip("\n")) <= 79:
            continue
        try:
            value = ast.literal_eval(token.string)
        except (ValueError, SyntaxError):
            continue
        if not isinstance(value, str) or len(repr(value)) <= 48:
            continue
        chunks = []
        chunk = ""
        for char in value:
            if chunk and len(repr(chunk + char)) > 48:
                chunks.append(repr(chunk))
                chunk = ""
            chunk += char
        if chunk:
            chunks.append(repr(chunk))
        start = offsets[token.start[0] - 1] + token.start[1]
        end = offsets[token.end[0] - 1] + token.end[1]
        replacements.append((start, end, "(\n" + "\n".join(chunks) + "\n)"))
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source


def format_source(source: str) -> str:
    """Apply Python 3.10-compatible Black formatting at PEP 8's 79 columns."""
    try:
        original = ast.parse(source, feature_version=(3, 10))
        wrapped = _split_long_literals(source)
        try:
            formatted = black.format_file_contents(
                wrapped,
                fast=False,
                mode=black.Mode(
                    line_length=79, target_versions={black.TargetVersion.PY310}
                ),
            )
        except black.NothingChanged:
            formatted = wrapped
        result = ast.parse(formatted, feature_version=(3, 10))
        if ast.dump(original) != ast.dump(result):
            raise FormattingError("formatting changed the generated program's AST")
        compile(formatted, "<generated>", "exec")
        return formatted
    except (SyntaxError, ValueError, AssertionError) as error:
        raise FormattingError(f"cannot format generated Python: {error}") from error
