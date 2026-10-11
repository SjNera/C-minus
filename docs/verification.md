# CLI feature verification

Local verification of C-Minus 0.2.0 completed on 2026-10-11 on macOS arm64. The
reference compiler reported `gcc-16 (Homebrew GCC 16.2.0) 16.2.0`. C programs were compiled with
`-std=c11 -Wall -Wextra -Werror=implicit-function-declaration -O0
-finput-charset=UTF-8 -fexec-charset=UTF-8`.

| Environment | Passed | Failed / errors | Skipped / expected failures |
| --- | ---: | ---: | ---: |
| Python 3.10.22, separate editable installation | 595 | 0 | 0 |
| Python 3.14.8, development environment | 595 | 0 | 0 |

The complete suites include all compiler stages, scoped binding and type checks,
CLI entry points, source diagnostics, standalone execution, exact C comparisons,
checker mismatches, missing tools, compilation errors, and subprocess timeouts.
Code-generation tests verify deterministic output and short-circuit side effects.
No stage tests remain marked as unfinished.

The added feature tests cover global initialization and visibility, shared writes,
compatible and conflicting prototypes, declared forward calls, mutual recursion,
UTF-8 output, and `printf` flags, width, precision, and dynamic fields. Generated
programs for all valid fixtures/examples pass pycodestyle 2.15.0 at 79 columns.
Formatting tests check AST equivalence, idempotence, long escaped strings, long
binding names, and preservation of an existing output file on formatting failure.
The environments used Black 26.10.1 on Python 3.10 and 26.10.0 on Python 3.14.

Pointer tests cover integer/boolean declarations, addresses, dereferencing,
indirect updates, aliases and rebinding, typed function parameters, recursion,
numeric parameter copies, global references, loop jumps, and address-taking in
initializers. Negative cases verify positioned errors for mismatched pointee
types, pointer arithmetic, multiple indirection, invalid addresses, pointer
returns, and unsupported formats.

Readability tests verify familiar names, short suffixes for shadowing and Python
collisions, ordinary assignments, selective conversions, and print/f-string
output. Against the installed 0.1.0 release, `hello.c` decreased from 134 generated
lines to 13; `factorial.c` decreased from 143 to 22. Both preserve their output.
The [generated pointer example](../examples/generated/pointers.py) uses a small
shared `Reference` class and `.value` reads/writes.

Loop-jump coverage includes `break` and `continue` in all three loop forms, all
nine nested pairs of loop types, shadowing at continuation points, exactly-once
step/condition side effects, empty `for` headers, positioned illegal-jump errors,
and semantic state recovery after an error.

An additional acceptance run generated all twenty-two `tests/gcc_cases/*.c` fixtures
and all five valid examples using Python 3.14.8. Each generated program ran with
`-I -S` under both Python 3.14.8 and Python 3.10.22, outside the repository.
All 27 cases matched their GNU GCC reference on stdout bytes, stderr bytes,
and process exit status. This includes a raw `0xff` output byte, exact trailing
whitespace, an empty program, a matching exit status of 7, UTF-8 byte counts,
and byte-limited string output. Every acceptance program also passed the style
checker and an independent raw-versus-formatted Python AST comparison.

[The machine-readable record](verification.json) contains the compiler identity,
Python and formatter versions, suite counts, readability line counts, and each
execution's stdout/stderr in hexadecimal with its exit status. It also records
style errors and AST comparisons.
Hex encoding preserves bytes that are not valid UTF-8.

Reproduce the main checks after installation:

```sh
CMINUS_CC=gcc python -m pytest -q
cminus-check examples/hello.c --cc gcc
cminus-check examples/factorial.c --cc gcc
cminus-check examples/loop_control.c --cc gcc
cminus-check examples/globals_and_recursion.c --cc gcc
cminus-check examples/pointers.c --cc gcc
cminus-check tests/gcc_cases/formatting.c --cc gcc
```

Use the installed GNU GCC executable in place of `gcc` where needed. The
[CI workflow](../.github/workflows/tests.yml) configures Python 3.10 and 3.14 on
Ubuntu with a GNU GCC identity check, zero skipped tests, example equivalence
checks, and independent generated-program execution.

The grammar and these fixtures define the verified subset. Results establish
behavior for the tested, defined C executions; they do not measure migration
time savings or establish general legacy-code compatibility. The
[requirements audit](requirements.md) maps the completed CLI scope and its
delimitations to the supplied study. The GitHub workflow is configured for these
checks; this record reports local runs, rather than a hosted CI execution.
