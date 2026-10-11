"""Core C behavior helpers and legacy utilities outside the source grammar."""

import sys


def parse_printf_format(format_str):
    """Return literal text and supported conversion specifications."""
    format_str = format_str.split("\0", 1)[0]
    parts = []
    index = 0
    while index < len(format_str):
        start = index
        while index < len(format_str) and format_str[index] != "%":
            index += 1
        if index > start:
            parts.append(format_str[start:index])
        if index == len(format_str):
            break
        index += 1
        if index < len(format_str) and format_str[index] == "%":
            parts.append("%")
            index += 1
            continue
        flags = ""
        while index < len(format_str) and format_str[index] in "-+ 0":
            flags += format_str[index]
            index += 1
        width = None
        if index < len(format_str) and format_str[index] == "*":
            width = "*"
            index += 1
        else:
            start = index
            while (
                index < len(format_str) and format_str[index] in "0123456789"
            ):
                index += 1
            if index > start:
                width = int(format_str[start:index])
        precision = None
        if index < len(format_str) and format_str[index] == ".":
            index += 1
            if index < len(format_str) and format_str[index] == "*":
                precision = "*"
                index += 1
            else:
                start = index
                while (
                    index < len(format_str)
                    and format_str[index] in "0123456789"
                ):
                    index += 1
                precision = int(format_str[start:index] or "0")
        if index == len(format_str):
            raise ValueError("incomplete printf format specifier '%'")
        conversion = format_str[index]
        index += 1
        if conversion not in {"d", "i", "c", "s"}:
            raise ValueError(
                f"unsupported printf format specifier '%{conversion}'"
            )
        if conversion in {"c", "s"} and any(flag != "-" for flag in flags):
            raise ValueError(f"invalid printf flags for '%{conversion}'")
        if conversion == "c" and precision is not None:
            raise ValueError("printf precision is invalid for '%c'")
        parts.append((flags, width, precision, conversion))
    return parts


def c_printf(format_str, *args):
    """Write C-style output bytes and return the byte count."""
    try:
        parts = parse_printf_format(format_str)
    except ValueError:
        # Legacy utility formats stay separate from the validated grammar.
        output = (format_str.split("\0", 1)[0] % args).encode("utf-8")
        sys.stdout.buffer.write(output)
        sys.stdout.flush()
        return len(output)
    return c_printf_parts(parts, *args)


def c_printf_parts(parts, *args):
    """Write a format already parsed by the compiler; return its byte count."""
    output = bytearray()
    argument = 0
    for part in parts:
        if isinstance(part, str):
            output.extend(part.encode("utf-8"))
            continue
        flags, width, precision, conversion = part
        if width == "*":
            width = int(args[argument])
            argument += 1
        if precision == "*":
            precision = int(args[argument])
            argument += 1
        width = 0 if width is None else width
        if width < 0:
            flags += "-"
            width = -width
        if precision is not None and precision < 0:
            precision = None
        value = args[argument]
        argument += 1
        if conversion in {"d", "i"}:
            number = int(value)
            sign = (
                "-"
                if number < 0
                else "+" if "+" in flags else " " if " " in flags else ""
            )
            digits = "" if number == 0 and precision == 0 else str(abs(number))
            if precision is not None:
                digits = digits.rjust(precision, "0")
            if "0" in flags and "-" not in flags and precision is None:
                digits = digits.rjust(max(0, width - len(sign)), "0")
            formatted = (sign + digits).encode("ascii")
        elif conversion == "c":
            formatted = bytes([int(value) % 256])
        else:
            formatted = value.split("\0", 1)[0].encode("utf-8")
            if precision is not None:
                formatted = formatted[:precision]
        padding = b" " * max(0, width - len(formatted))
        output.extend(
            formatted + padding if "-" in flags else padding + formatted
        )
    sys.stdout.buffer.write(output)
    sys.stdout.flush()
    return len(output)


def write_text(text):
    """Write exact UTF-8 output and return the number of bytes written."""
    data = text.encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.flush()
    return len(data)


class Reference:
    """Shared storage for an int or bool whose address is used."""

    def __init__(self, value):
        self.value = value


def set_value(reference, value):
    """Preserve the result of a C assignment used inside another expression."""
    reference.value = value
    return value


def c_scanf(format_str, *pointers):
    """
    Emulates C-style scanf reading input into reference/pointer objects.
    """
    raw_inputs = input().split()
    specifiers = format_str.split()

    for idx, ptr in enumerate(pointers):
        if idx >= len(raw_inputs):
            break
        val = raw_inputs[idx]
        spec = specifiers[idx] if idx < len(specifiers) else "%s"

        if "%d" in spec or "%i" in spec:
            ptr.set(int(val))
        elif "%f" in spec or "%lf" in spec:
            ptr.set(float(val))
        elif "%c" in spec:
            ptr.set(val[0] if val else "")
        else:
            ptr.set(str(val))


def c_int_div(a, b):
    """Divide integers with truncation toward zero."""
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


def c_int_mod(a, b):
    """Return C's remainder with the dividend's sign."""
    return a - b * c_int_div(a, b)


class Pointer:
    """Simulates C-style pointers and pass-by-reference mutable references."""

    def __init__(self, value=None):
        self.val = value

    def set(self, value):
        self.val = value

    def get(self):
        return self.val


def run_gcc_comparison(c_file_path, generated_py_file_path, test_input=""):
    """
    Compiles and executes the original C file with GCC, runs the transpiled
    Python file, and compares stdout, stderr, and exit status exactly.
    """
    from cminus.extras.gcc_equivalence import compare_files

    result = compare_files(
        c_file_path,
        generated_py_file_path,
        stdin=test_input.encode(),
        isolated=False,
    )
    return (
        result.equivalent,
        result.c.stdout.decode(),
        result.python.stdout.decode(),
    )
