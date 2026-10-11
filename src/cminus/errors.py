"""Shared error hierarchy for positioned compiler diagnostics.

Every source phase raises a subclass of CMinusError. CLI boundaries render them.
"""

from __future__ import annotations

from typing import Optional


class CMinusError(Exception):
    kind = "error"

    def __init__(
        self, message: str, line: Optional[int] = None, column: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        if self.line is None:
            return f"{self.kind}: {self.message}"
        col = f":{self.column}" if self.column is not None else ""
        return f"{self.line}{col}: {self.kind}: {self.message}"


class LexicalError(CMinusError):
    kind = "lexical error"


class ParseError(CMinusError):
    kind = "syntax error"


class SemanticError(CMinusError):
    kind = "semantic error"
