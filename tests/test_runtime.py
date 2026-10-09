"""Pending C arithmetic and supported printf runtime behavior."""

import pytest

from cminus.c_runtime import c_div, c_mod, printf

pytestmark = pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="runtime helpers are not implemented yet",
)


@pytest.mark.parametrize(
    "a,b,quotient,remainder",
    [
        (7, 3, 2, 1),
        (-7, 3, -2, -1),
        (7, -3, -2, 1),
        (-7, -3, 2, -1),
        (6, 3, 2, 0),
        (-6, 3, -2, 0),
        (0, 3, 0, 0),
        (1, 3, 0, 1),
        (-1, 3, 0, -1),
        (2**60 + 2, 3, 384307168202282326, 0),
    ],
)
def test_division_truncates_toward_zero_and_remainder_keeps_dividend_sign(
    a: int,
    b: int,
    quotient: int,
    remainder: int,
) -> None:
    actual_quotient = c_div(a, b)
    actual_remainder = c_mod(a, b)
    assert type(actual_quotient) is int and type(actual_remainder) is int
    assert actual_quotient == quotient
    assert actual_remainder == remainder
    assert a == actual_quotient * b + actual_remainder


@pytest.mark.parametrize("helper", [c_div, c_mod], ids=["division", "modulo"])
def test_zero_divisor_raises_a_runtime_error(helper) -> None:
    with pytest.raises(ZeroDivisionError):
        helper(5, 0)


@pytest.mark.parametrize(
    "fmt,args,expected",
    [
        ("", (), ""),
        ("hello\n", (), "hello\n"),
        ("100%%", (), "100%"),
        ("%d %i", (7, -3), "7 -3"),
        ("%d %i", (True, False), "1 0"),
        ("%c", (65,), "A"),
        ("%s", ("text",), "text"),
        ("%%%d", (42,), "%42"),
        ("%d %i %c %s %%", (7, -3, 65, "ok"), "7 -3 A ok %"),
    ],
)
def test_printf_writes_supported_formats_and_returns_character_count(
    fmt: str,
    args: tuple,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    count = printf(fmt, *args)
    output = capsys.readouterr()
    assert output.out == expected
    assert output.err == ""
    assert count == len(expected)
