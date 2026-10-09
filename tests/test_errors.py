"""Diagnostic formatting and the common compiler exception contract."""

import pytest

from cminus.errors import CMinusError, LexicalError, ParseError, SemanticError


@pytest.mark.parametrize(
    "error_type,kind",
    [
        (CMinusError, "error"),
        (LexicalError, "lexical error"),
        (ParseError, "syntax error"),
        (SemanticError, "semantic error"),
    ],
)
@pytest.mark.parametrize(
    "line,column,prefix",
    [
        (None, None, ""),
        (None, 5, ""),
        (8, None, "8: "),
        (8, 5, "8:5: "),
        (0, 0, "0:0: "),
    ],
)
def test_error_formatting_and_metadata(
    error_type: type[CMinusError],
    kind: str,
    line: int | None,
    column: int | None,
    prefix: str,
) -> None:
    error = error_type("invalid input", line, column)

    assert str(error) == f"{prefix}{kind}: invalid input"
    assert error.message == "invalid input"
    assert (error.line, error.column) == (line, column)
    assert error.args == ("invalid input",)


@pytest.mark.parametrize("error_type", [LexicalError, ParseError, SemanticError])
def test_pipeline_can_catch_every_phase_error_as_cminus_error(
    error_type: type[CMinusError],
) -> None:
    error = error_type("failure", 2, 3)
    with pytest.raises(CMinusError) as caught:
        raise error
    assert caught.value is error


def test_error_message_preserves_multiline_unicode_text() -> None:
    message = "unexpected café\nsecond line"
    assert str(SemanticError(message, 1, 2)) == f"1:2: semantic error: {message}"
