"""Compare original C and Python output, errors, and process exit status."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from cminus import __version__
from cminus.compiler import compile_source
from cminus.errors import CMinusError
from cminus.extras.error_reporter import render_error


class CheckError(RuntimeError):
    """Compilation, tool, or execution failure that prevents comparison."""


@dataclass
class Comparison:
    c: subprocess.CompletedProcess
    python: subprocess.CompletedProcess
    compiler: str

    @property
    def equivalent(self) -> bool:
        return (self.c.stdout, self.c.stderr, self.c.returncode) == (
            self.python.stdout,
            self.python.stderr,
            self.python.returncode,
        )

    def differences(self) -> list[str]:
        return [
            f"{field}: C={getattr(self.c, field)!r}; Python={getattr(self.python, field)!r}"
            for field in ("stdout", "stderr", "returncode")
            if getattr(self.c, field) != getattr(self.python, field)
        ]


def _run(command, *, timeout, stdin=b""):
    try:
        return subprocess.run(
            command, input=stdin, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as error:
        raise CheckError(f"timed out after {timeout:g}s: {command[0]}") from error
    except OSError as error:
        raise CheckError(f"cannot run {command[0]}: {error}") from error


def compare_files(
    c_file_path,
    generated_py_file_path,
    *,
    compiler=None,
    timeout=10.0,
    stdin=b"",
    isolated=True,
) -> Comparison:
    compiler = compiler or os.environ.get("CMINUS_CC", "gcc")
    identity = _run([compiler, "--version"], timeout=timeout)
    if identity.returncode:
        raise CheckError("cannot identify the C compiler")
    version = identity.stdout.decode("utf-8", errors="replace").splitlines()
    name = version[0] if version else compiler
    # Resolve before entering the temporary build directory.
    c_file = str(Path(c_file_path).resolve())
    py_file = str(Path(generated_py_file_path).resolve())
    with tempfile.TemporaryDirectory(prefix="cminus-check-") as directory:
        executable = str(
            Path(directory) / ("program.exe" if os.name == "nt" else "program")
        )
        built = _run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror=implicit-function-declaration",
                "-O0",
                "-finput-charset=UTF-8",
                "-fexec-charset=UTF-8",
                c_file,
                "-o",
                executable,
            ],
            timeout=timeout,
        )
        if built.returncode:
            raise CheckError(
                "C compilation failed:\n"
                + built.stderr.decode("utf-8", errors="replace")
            )
        c_result = _run([executable], timeout=timeout, stdin=stdin)
        python_command = [sys.executable, "-I", "-S"] if isolated else [sys.executable]
        python_result = _run([*python_command, py_file], timeout=timeout, stdin=stdin)
    return Comparison(c_result, python_result, name)


def _positive_timeout(value):
    try:
        timeout = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout must be a positive number") from error
    if not 0 < timeout < float("inf"):
        raise argparse.ArgumentTypeError("timeout must be a positive finite number")
    return timeout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cminus-check", description="Compare C-Minus output against a C11 compiler"
    )
    parser.add_argument(
        "--version", action="version", version=f"cminus-check {__version__}"
    )
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument(
        "--cc", default=os.environ.get("CMINUS_CC", "gcc"), help="C compiler executable"
    )
    parser.add_argument(
        "--timeout",
        type=_positive_timeout,
        default=10.0,
        help="seconds per compilation or execution",
    )
    args = parser.parse_args(argv)
    if args.input is None:
        parser.print_help()
        return 0
    source = ""
    try:
        source = args.input.read_text(encoding="utf-8")
        compilation = compile_source(source)
        with tempfile.TemporaryDirectory(prefix="cminus-python-") as directory:
            script = Path(directory) / "program.py"
            script.write_text(compilation.python_source, encoding="utf-8")
            result = compare_files(
                args.input, script, compiler=args.cc, timeout=args.timeout
            )
        print(f"Compiler: {result.compiler}")
        if result.equivalent:
            print(f"Equivalent: stdout, stderr, exit status ({result.c.returncode})")
            return 0
        print("Mismatch:", file=sys.stderr)
        for difference in result.differences():
            print(difference, file=sys.stderr)
        return 1
    except CMinusError as error:
        print(render_error(error, str(args.input), source), file=sys.stderr)
        return 2
    except (CheckError, OSError, UnicodeError) as error:
        print(f"cminus-check: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
