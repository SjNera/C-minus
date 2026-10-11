"""Deterministic text representations for teaching and debugging."""

from pprint import pformat


def dump_tokens(tokens) -> str:
    return "\n".join(
        f"{token.line}:{token.column} {token.type} {token.lexeme!r}" for token in tokens
    )


def dump_ast(program) -> str:
    return pformat(program, width=88, sort_dicts=True)
