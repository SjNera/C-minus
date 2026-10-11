"""Core C behavior helpers and legacy utilities outside the source grammar."""

import sys

# =====================================================================
# ROLE 1: C-Behavior Emulation Runtime Library
# =====================================================================


def c_printf(format_str, *args):
    """
    Emulates C-style printf output behavior.
    Handles standard format specifiers without auto-appending standard Python newlines
    unless explicitly included in format_str (\n).
    """
    format_str = format_str.split("\0", 1)[0]
    output = bytearray()
    index = argument = 0
    while index < len(format_str):
        char = format_str[index]
        index += 1
        if char != "%":
            output.extend(char.encode("utf-8"))
            continue
        if index == len(format_str):
            raise ValueError("incomplete printf format")
        specifier = format_str[index]
        index += 1
        if specifier not in ("%", "d", "i", "c", "s"):
            # Preserve the legacy Python-format utility; the source compiler
            # rejects these advanced specifiers before code generation.
            legacy_output = (format_str % args).encode("utf-8")
            sys.stdout.buffer.write(legacy_output)
            sys.stdout.flush()
            return len(legacy_output)
        if specifier == "%":
            output.extend(b"%")
            continue
        value = args[argument]
        argument += 1
        if specifier in ("d", "i"):
            output.extend(str(int(value)).encode("ascii"))
        elif specifier == "c":
            output.append(int(value) % 256)
        elif specifier == "s":
            output.extend(value.split("\0", 1)[0].encode("utf-8"))
        else:
            raise ValueError(f"unsupported printf format '%{specifier}'")
    sys.stdout.buffer.write(output)
    sys.stdout.flush()
    return len(output)


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
    """
    Emulates C integer division (truncation towards zero) where 5 / 2 = 2.
    """
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


def c_int_mod(a, b):
    """
    Emulates C remainder: the result has the sign of the dividend (-7 % 3 = -1).
    """
    return a - b * c_int_div(a, b)


class Pointer:
    """Simulates C-style pointers and pass-by-reference mutable references."""

    def __init__(self, value=None):
        self.val = value

    def set(self, value):
        self.val = value

    def get(self):
        return self.val


# =====================================================================
# ROLE 2: GCC Equivalence & Output Testing Environment
# =====================================================================


def run_gcc_comparison(c_file_path, generated_py_file_path, test_input=""):
    """
    Compiles and executes the original C file with GCC, runs the transpiled
    Python file, and compares stdout, stderr, and exit status exactly.
    """
    from cminus.extras.gcc_equivalence import compare_files

    result = compare_files(
        c_file_path, generated_py_file_path, stdin=test_input.encode(), isolated=False
    )
    return result.equivalent, result.c.stdout.decode(), result.python.stdout.decode()
