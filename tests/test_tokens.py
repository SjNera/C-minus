"""Token metadata passed from the lexer to the parser."""

from cminus.tokens import Token


def test_token_preserves_source_text_and_location() -> None:
    token = Token("STRING", '"hello\\n"', 4, 9)
    assert token.type == "STRING"
    assert token.lexeme == '"hello\\n"'
    assert (token.line, token.column) == (4, 9)


def test_repeated_lexemes_keep_distinct_source_locations() -> None:
    first = Token("IDENTIFIER", "count", 2, 5)
    second = Token("IDENTIFIER", "count", 8, 12)
    second.line = 9

    assert first.lexeme == second.lexeme == "count"
    assert (first.line, first.column) == (2, 5)
    assert (second.line, second.column) == (9, 12)
