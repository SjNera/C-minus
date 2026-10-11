"""Check installed CLI commands without relying on the source checkout."""

import argparse
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

import cminus

PROGRAM = """#include <stdio.h>
int calls;
int add(int);
int main(void) {
    int total = 0;
    for (int i = 0; i < 6; i = i + 1) {
        if (i == 1) continue;
        if (i == 4) break;
        total = add(i);
    }
    printf("total=%03d calls=%d café\\n", total, calls);
    return 7;
}
int add(int value) {
    calls = calls + 1;
    return value + 10;
}
"""
EXPECTED = "total=013 calls=3 café\n".encode("utf-8")


def run(command, directory):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [str(part) for part in command],
        cwd=directory,
        env=environment,
        capture_output=True,
        timeout=30,
    )


def check_result(result, stdout, status=0):
    assert (result.stdout, result.stderr, result.returncode) == (
        stdout,
        b"",
        status,
    ), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default=os.environ.get("CMINUS_CC", "gcc"))
    args = parser.parse_args()
    installed = distribution("cminus")
    direct_url = json.loads(installed.read_text("direct_url.json") or "{}")
    assert not direct_url.get("dir_info", {}).get(
        "editable"
    ), "Use a regular wheel or source-distribution install for this check."
    assert cminus.__version__ == installed.version
    assert "site-packages" in Path(cminus.__file__).parts, cminus.__file__
    suffix = ".exe" if sys.platform == "win32" else ""
    scripts = Path(sysconfig.get_path("scripts"))
    compiler = scripts / ("cminus" + suffix)
    checker = scripts / ("cminus-check" + suffix)

    with tempfile.TemporaryDirectory(prefix="cminus-install-") as directory:
        for name, executable in [("cminus", compiler), ("cminus-check", checker)]:
            check_result(
                run([executable, "--version"], directory),
                f"{name} {installed.version}\n".encode(),
            )
            help_result = run([executable, "--help"], directory)
            assert help_result.returncode == 0 and not help_result.stderr
            assert f"usage: {name}".encode() in help_result.stdout
        check_result(
            run([sys.executable, "-I", "-m", "cminus", "--version"], directory),
            f"cminus {installed.version}\n".encode(),
        )
        source = Path(directory) / "program with spaces.c"
        generated = Path(directory) / "program with spaces.py"
        source.write_text(PROGRAM, encoding="utf-8")
        check_result(
            run([compiler, source, "-o", generated, "--run"], directory),
            EXPECTED,
            status=7,
        )
        check_result(
            run([sys.executable, "-I", "-S", generated], directory),
            EXPECTED,
            status=7,
        )
        comparison = run([checker, source, "--cc", args.cc], directory)
        assert comparison.returncode == 0 and not comparison.stderr, comparison
        assert b"Equivalent: stdout, stderr, exit status (7)" in comparison.stdout
        invalid = Path(directory) / "invalid.c"
        invalid.write_text("int main(void) { return missing; }", encoding="utf-8")
        error = run([compiler, invalid], directory)
        assert error.returncode == 1 and not error.stdout, error
        assert b"semantic error" in error.stderr and b"^" in error.stderr
        assert b"missing" in error.stderr and b"Traceback" not in error.stderr

    print(f"Installed cminus {installed.version}: both CLI commands passed.")
    print(f"Package: {cminus.__file__}")
    print("Standalone output and C11 equivalence passed outside the checkout.")


if __name__ == "__main__":
    main()
