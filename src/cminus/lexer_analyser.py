"""Tokenize the C-Minus core while retaining source text and positions."""

from __future__ import annotations

import re

from cminus.errors import LexicalError
from cminus.tokens import Token

KEYWORDS = {
    "int",
    "bool",
    "void",
    "if",
    "else",
    "while",
    "do",
    "for",
    "return",
    "break",
    "continue",
    "float",
    "double",
    "string",
    "char",
    "struct",
    "union",
    "enum",
    "typedef",
    "short",
    "long",
    "unsigned",
    "signed",
    "switch",
    "case",
    "goto",
    "static",
    "const",
    "extern",
}
ESCAPES = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "0": "\0",
    "\\": "\\",
    '"': '"',
    "'": "'",
    "?": "?",
}
_INCLUDE = re.compile(r"#[ \t]*include[ \t]*<([A-Za-z0-9_.]+)>")
_DOUBLE = {"==", "!=", "<=", ">=", "&&", "||"}
_UNSUPPORTED = {
    "++",
    "--",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
    "<<",
    ">>",
    "->",
}


def decode_string(lexeme: str) -> str:
    """Decode a string token already checked by the lexer."""
    result = []
    index = 1
    while index < len(lexeme) - 1:
        char = lexeme[index]
        if char == "\\":
            index += 1
            char = ESCAPES[lexeme[index]]
        result.append(char)
        index += 1
    return "".join(result)


def tokenize(source: str) -> list[Token]:
    """Return shared tokens, including EOF, or raise a positioned LexicalError."""
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    tokens: list[Token] = []
    index = 0
    line = column = 1

    def advance(count: int = 1) -> None:
        nonlocal index, line, column
        for _ in range(count):
            if source[index] == "\n":
                line += 1
                column = 1
            else:
                column += 1
            index += 1

    while index < len(source):
        char = source[index]
        if char in " \t\n\f\v":
            advance()
            continue
        start, start_line, start_column = index, line, column
        pair = source[index : index + 2]
        if pair == "//":
            while index < len(source) and source[index] != "\n":
                advance()
            continue
        if pair == "/*":
            advance(2)
            while index < len(source) and source[index : index + 2] != "*/":
                advance()
            if index == len(source):
                raise LexicalError(
                    "unterminated block comment", start_line, start_column
                )
            advance(2)
            continue
        if char == "#":
            if source[source.rfind("\n", 0, index) + 1 : index].strip():
                raise LexicalError(
                    "an include must start a source line", line, column
                )
            match = _INCLUDE.match(source, index)
            if match is None:
                raise LexicalError(
                    "only virtual standard-header includes are supported",
                    line,
                    column,
                )
            if match.group(1) not in {"stdio.h", "stdbool.h"}:
                raise LexicalError(
                    f"unsupported header <{match.group(1)}>", line, column
                )
            tail = source[match.end() :].split("\n", 1)[0]
            if not re.fullmatch(r"[ \t]*(?://.*|/\*.*?\*/[ \t]*)?", tail):
                raise LexicalError(
                    "unexpected text after include directive", line, column
                )
            advance(len(match.group()))
            kind = "INCLUDE"
        elif char.isascii() and (char.isalpha() or char == "_"):
            advance()
            while index < len(source):
                next_char = source[index]
                if not next_char.isascii() or not (
                    next_char.isalnum() or next_char == "_"
                ):
                    break
                advance()
            word = source[start:index]
            kind = (
                "BOOL"
                if word in {"true", "false"}
                else "KEYWORD" if word in KEYWORDS else "IDENTIFIER"
            )
        elif char in "0123456789":
            advance()
            while index < len(source) and source[index] in "0123456789":
                advance()
            number = source[start:index]
            if (len(number) > 1 and number[0] == "0") or (
                index < len(source)
                and (source[index].isalnum() or source[index] in "._")
            ):
                raise LexicalError(
                    "only decimal integer literals are supported",
                    start_line,
                    start_column,
                )
            kind = "INT"
        elif char == '"':
            advance()
            while index < len(source) and source[index] != '"':
                if source[index] == "\n":
                    raise LexicalError(
                        "unterminated string literal", start_line, start_column
                    )
                if source[index] == "\\":
                    escape_line, escape_column = line, column
                    advance()
                    if index == len(source) or source[index] not in ESCAPES:
                        raise LexicalError(
                            "unsupported or unfinished string escape",
                            escape_line,
                            escape_column,
                        )
                    if (
                        source[index] == "0"
                        and index + 1 < len(source)
                        and source[index + 1].isdigit()
                    ):
                        raise LexicalError(
                            "octal escapes are outside the core",
                            escape_line,
                            escape_column,
                        )
                advance()
            if index == len(source):
                raise LexicalError(
                    "unterminated string literal", start_line, start_column
                )
            advance()
            kind = "STRING"
        elif pair in _UNSUPPORTED:
            raise LexicalError(
                f"operator '{pair}' is outside the core", line, column
            )
        elif pair in _DOUBLE:
            advance(2)
            kind = pair
        elif char in "+-*/%<>=!&(){};,":
            advance()
            kind = char
        else:
            raise LexicalError(f"unsupported character '{char}'", line, column)
        tokens.append(
            Token(kind, source[start:index], start_line, start_column)
        )
    tokens.append(Token("EOF", "", line, column))
    return tokens
