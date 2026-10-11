"""Shared tokens: named literal/keyword classes and literal punctuation types."""

from dataclasses import dataclass


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int
