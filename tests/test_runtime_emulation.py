"""Tests for cminus.runtime: unit tests plus a comparison against real GCC output.

Run from the repo root:   python -m pytest tests/test_runtime_emulation.py -v
The GCC comparison is skipped automatically when gcc is not installed.
"""
import shutil
import sys
import textwrap

import pytest

from cminus.runtime import (
    Pointer, c_int_div, c_int_mod, c_printf, c_scanf, run_gcc_comparison,
)


# ----------------------------------------------------------------- c_printf
def test_printf_formats_arguments(capsys):
    c_printf("%d + %d = %d\n", 1, 2, 3)
    assert capsys.readouterr().out == "1 + 2 = 3\n"


def test_printf_no_arguments_prints_literal_percent(capsys):
    c_printf("100%%\n")  # C prints 100%
    assert capsys.readouterr().out == "100%\n"


def test_printf_does_not_add_newline(capsys):
    c_printf("a")
    c_printf("b")
    assert capsys.readouterr().out == "ab"


# ------------------------------------------------------------ division / mod
@pytest.mark.parametrize("a, b, expected", [
    (5, 2, 2), (-5, 2, -2), (5, -2, -2), (-5, -2, 2), (7, 7, 1), (0, 3, 0),
])
def test_int_div_truncates_toward_zero(a, b, expected):
    assert c_int_div(a, b) == expected


@pytest.mark.parametrize("a, b, expected", [
    (7, 3, 1), (-7, 3, -1), (7, -3, 1), (-7, -3, -1), (6, 3, 0),
])
def test_int_mod_takes_sign_of_dividend(a, b, expected):
    assert c_int_mod(a, b) == expected


# ------------------------------------------------------------------ pointers
def test_pointer_get_set():
    p = Pointer(5)
    assert p.get() == 5
    p.set(9)
    assert p.get() == 9


# -------------------------------------------------------------------- scanf
def test_scanf_reads_ints_and_floats(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda: "3 4.5")
    a, b = Pointer(), Pointer()
    c_scanf("%d %f", a, b)
    assert (a.get(), b.get()) == (3, 4.5)


# ------------------------------------------------------------- GCC comparison
C_SOURCE = textwrap.dedent(r'''
    #include <stdio.h>
    int main() {
        printf("%d %d %d %d\n", 7 / 2, -7 / 2, -7 % 3, 7 % -3);
        printf("100%%\n");
        printf("%5.2f|%s|%c|%x\n", 3.14159, "hi", 'A', 255);
        return 0;
    }
''')

PY_SOURCE = textwrap.dedent(r'''
    from cminus.runtime import c_printf, c_int_div, c_int_mod
    c_printf("%d %d %d %d\n", c_int_div(7, 2), c_int_div(-7, 2), c_int_mod(-7, 3), c_int_mod(7, -3))
    c_printf("100%%\n")
    c_printf("%5.2f|%s|%c|%x\n", 3.14159, "hi", 65, 255)
''')


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc is not installed")
def test_runtime_output_matches_gcc(tmp_path):
    c_file = tmp_path / "program.c"
    py_file = tmp_path / "program.py"
    c_file.write_text(C_SOURCE)
    py_file.write_text(PY_SOURCE)

    equivalent, gcc_out, py_out = run_gcc_comparison(str(c_file), str(py_file))
    assert equivalent, f"GCC printed {gcc_out!r} but the Python version printed {py_out!r}"
