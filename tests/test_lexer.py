"""lexer contracts; token type and EOF conventions remain unspecified."""

import pytest

from cminus.errors import LexicalError
from cminus.lexer_analyser import tokenize
from cminus.tokens import Token


def test_tokens_preserve_lexemes_and_one_based_source_locations() -> None:
    tokens = tokenize("int main() {\n    return 42;\n}\n")
    expected = [
        ("int", 1, 1),
        ("main", 1, 5),
        ("(", 1, 9),
        (")", 1, 10),
        ("{", 1, 12),
        ("return", 2, 5),
        ("42", 2, 12),
        (";", 2, 14),
        ("}", 3, 1),
    ]
    assert all(isinstance(token, Token) for token in tokens)
    assert [
        (token.lexeme, token.line, token.column) for token in tokens[: len(expected)]
    ] == expected


@pytest.mark.parametrize(
    "operator",
    ["+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=", "&&", "||", "!", "="],
)
def test_supported_operators_are_not_split(operator: str) -> None:
    tokens = tokenize(f"a {operator} b")
    assert [token.lexeme for token in tokens[:3]] == ["a", operator, "b"]
    assert (tokens[1].line, tokens[1].column) == (1, 3)


@pytest.mark.parametrize("source", ["@", '"unterminated'])
def test_invalid_source_raises_a_lexical_error(source: str) -> None:
    with pytest.raises(LexicalError):
        tokenize(source)
