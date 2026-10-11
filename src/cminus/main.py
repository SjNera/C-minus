"""Command-line translation, inspection, and execution of C-Minus programs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from cminus import __version__
from cminus.compiler import compile_source
from cminus.errors import CMinusError
from cminus.extras.error_reporter import render_error
from cminus.extras.introspection import dump_ast, dump_tokens


def _write_output(destination: Path, source: str) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(source)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cminus", description="C-Minus: C subset to Python compiler"
    )
    parser.add_argument("--version", action="version", version=f"cminus {__version__}")
    parser.add_argument("input", nargs="?", type=Path, help="C-Minus source file")
    parser.add_argument(
        "-o", "--output", type=Path, help="write standalone Python to this file"
    )
    parser.add_argument(
        "--run", action="store_true", help="execute the generated program"
    )
    parser.add_argument(
        "--dump-tokens", action="store_true", help="print tokens to stderr"
    )
    parser.add_argument(
        "--dump-ast", action="store_true", help="print the typed AST to stderr"
    )
    parser.add_argument(
        "--dump-symbols", action="store_true", help="print symbol tables to stderr"
    )
    parser.add_argument(
        "--verbose-passes", action="store_true", help="report compiler passes to stderr"
    )
    args = parser.parse_args(argv)
    if args.input is None:
        if any(
            (
                args.output,
                args.run,
                args.dump_tokens,
                args.dump_ast,
                args.dump_symbols,
                args.verbose_passes,
            )
        ):
            parser.error("an input file is required")
        parser.print_help()
        return 0
    source = ""
    try:
        source = args.input.read_text(encoding="utf-8")
        observer = (
            (lambda name: print(f"[cminus] {name}", file=sys.stderr))
            if args.verbose_passes
            else None
        )
        result = compile_source(source, observer)
        if args.dump_tokens:
            print("Tokens:\n" + dump_tokens(result.tokens), file=sys.stderr)
        if args.dump_ast:
            print("AST:\n" + dump_ast(result.program), file=sys.stderr)
        if args.dump_symbols:
            print("Symbols:\n" + result.symbols.dump(), file=sys.stderr)
        if args.output is not None:
            if args.output.resolve() == args.input.resolve():
                raise OSError("output path must differ from the input source")
            _write_output(args.output, result.python_source)
        if args.run:
            with tempfile.TemporaryDirectory(prefix="cminus-run-") as directory:
                script = Path(directory) / "program.py"
                script.write_text(result.python_source, encoding="utf-8")
                return subprocess.run(
                    [sys.executable, "-I", "-S", str(script)]
                ).returncode
        if args.output is None:
            sys.stdout.write(result.python_source)
        return 0
    except CMinusError as error:
        print(render_error(error, str(args.input), source), file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(f"cminus: {error}", file=sys.stderr)
        return 1
