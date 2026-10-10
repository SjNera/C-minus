import os
import subprocess
import sys
import tempfile

# =====================================================================
# ROLE 1: C-Behavior Emulation Runtime Library
# =====================================================================

def c_printf(format_str, *args):
    """
    Emulates C-style printf output behavior.
    Handles standard format specifiers without auto-appending standard Python newlines
    unless explicitly included in format_str (\n).
    """
    # Always format, even with no arguments, so "100%%" prints "100%" like C.
    output = format_str % args
    sys.stdout.write(output)
    sys.stdout.flush()


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
    return int(a / b)


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
    Python file, and compares their stdout to verify exact equivalence.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        exe_path = os.path.join(temp_dir, "c_out.exe" if os.name == 'nt' else "c_out")

        # 1. Compile C file using GCC
        try:
            compile_cmd = ["gcc", c_file_path, "-o", exe_path]
            compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise FileNotFoundError("GCC compiler is not installed or not found in system PATH.") from e

        if compile_proc.returncode != 0:
            raise RuntimeError(f"GCC Compilation Failed:\n{compile_proc.stderr}")

        # 2. Run compiled C executable
        c_proc = subprocess.run(
            [exe_path],
            input=test_input,
            capture_output=True,
            text=True
        )
        gcc_output = c_proc.stdout

        # 3. Run generated Python file
        py_proc = subprocess.run(
            [sys.executable, generated_py_file_path],
            input=test_input,
            capture_output=True,
            text=True
        )
        python_output = py_proc.stdout

        # 4. Compare outputs
        is_equivalent = (gcc_output.strip() == python_output.strip())
        return is_equivalent, gcc_output, python_output