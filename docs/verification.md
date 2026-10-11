# Working-core verification

Local verification completed on 2026-10-10 on macOS arm64. The reference compiler
reported `gcc-16 (Homebrew GCC 16.2.0) 16.2.0`. C programs were compiled with
`-std=c11 -Wall -Wextra -Werror=implicit-function-declaration -O0`.

| Environment | Passed | Failed / errors | Skipped / expected failures |
| --- | ---: | ---: | ---: |
| Python 3.10.22, fresh editable installation | 440 | 0 | 0 |
| Python 3.14.8, development environment | 440 | 0 | 0 |

The complete suites include all compiler stages, scoped binding and type checks,
CLI entry points, source diagnostics, standalone execution, exact C comparisons,
checker mismatches, missing tools, compilation errors, and subprocess timeouts.
Code-generation tests verify deterministic output and short-circuit side effects.
No stage tests remain marked as unfinished.

An additional acceptance run generated all nine `tests/gcc_cases/*.c` fixtures
and both valid examples using Python 3.14.8. Each generated program ran with
`-I -S` under both Python 3.14.8 and Python 3.10.22, outside the repository.
All 11 cases matched their GNU GCC reference on stdout bytes, stderr bytes,
and process exit status. This includes a raw `0xff` output byte, exact trailing
whitespace, an empty program, and a matching exit status of 7.

[The machine-readable record](verification.json) contains the compiler identity,
Python versions, suite counts, and each execution's stdout/stderr in hexadecimal
with its exit status. Hex encoding preserves bytes that are not valid UTF-8.

Reproduce the main checks after installation:

```sh
CMINUS_CC=gcc python -m pytest -q
cminus-check examples/hello.c --cc gcc
cminus-check examples/factorial.c --cc gcc
cminus-check tests/gcc_cases/formatting.c --cc gcc
```

Use the installed GNU GCC executable in place of `gcc` where needed. The
[CI workflow](../.github/workflows/tests.yml) configures Python 3.10 and 3.14 on
Ubuntu with a GNU GCC identity check, zero skipped tests, example equivalence
checks, and independent generated-program execution.

The grammar and these fixtures define the verified core. Results establish
behavior for the tested, defined C executions; they do not measure migration
time savings or establish general legacy-code compatibility. The broader study's
deferred features are listed in the [project scope](../README.md#implemented-scope).
