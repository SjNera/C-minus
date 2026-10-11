"""Run lexical, syntax, semantic, generation, and formatting passes."""

from dataclasses import dataclass
from typing import Callable

from cminus.ast_nodes import Program
from cminus.code_generator import generate
from cminus.extras.formatter import format_source
from cminus.lexer_analyser import tokenize
from cminus.parser import parse
from cminus.semantic_analyser import SymbolTable, analyse
from cminus.tokens import Token


@dataclass
class Compilation:
    tokens: list[Token]
    program: Program
    symbols: SymbolTable
    python_source: str


def compile_source(
    source: str, on_pass: Callable[[str], None] | None = None
) -> Compilation:
    def report(name: str) -> None:
        if on_pass is not None:
            on_pass(name)

    report("lexical analysis")
    tokens = tokenize(source)
    report("syntax analysis")
    program = parse(tokens)
    report("semantic analysis")
    symbols = analyse(program)
    report("code generation")
    python_source = generate(program, symbols)
    report("Python formatting")
    python_source = format_source(python_source)
    return Compilation(tokens, program, symbols, python_source)
