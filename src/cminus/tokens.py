"""Shared token definitions. Owner: Module 1 (Hilarie Cipriano).

Replace `type: str` with a TokenType enum once the token list is agreed.
"""
from dataclasses import dataclass


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    column: int
