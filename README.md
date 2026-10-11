# C-Minus: From C to Python

A working educational source-to-source compiler for a defined subset of C. The
pipeline tokenizes source, builds a shared AST, checks types and lexical scopes,
and generates standalone Python 3.10+ programs.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
cminus --version
```

The compiler has no third-party runtime dependencies. Development dependencies
provide pytest and Black. A C11 compiler is needed for equivalence checks.

## Translate, run, and inspect

```sh
cminus examples/hello.c -o /tmp/hello.py
python -I -S /tmp/hello.py
cminus examples/factorial.c --run
cminus examples/factorial.c --dump-tokens --dump-ast --dump-symbols --verbose-passes -o /tmp/factorial.py
cminus-check examples/factorial.c --cc gcc --timeout 10
```

Without `-o` or `--run`, generated code goes to stdout. Inspection output goes to
stderr. `--run` forwards the generated program's output and exit status. Output
files are replaced only after successful compilation; diagnostics include the
filename, line, column, source text, and a caret.

Generated programs embed the arithmetic and output helpers they use. They run
outside this repository without an installed C-Minus package. The reusable API is:

```python
from cminus.compiler import compile_source

result = compile_source('int main(void) { return 0; }')
print(result.python_source)
```

`cminus-check` compares stdout bytes, stderr bytes, and exit status exactly. It
returns 0 for equivalence (including matching nonzero program exits), 1 for a
mismatch, and 2 for source, compiler, or timeout failures. `--timeout` applies to
each subprocess. Select a compiler with `--cc` or `CMINUS_CC`; the checker prints
its identity. On macOS, `gcc` may select Apple Clang; use the versioned GNU GCC
executable installed by Homebrew when verifying with GNU GCC.

## Implemented scope

| Area | Working core |
| --- | --- |
| Values | Decimal `int`, `bool`, and ASCII string literals |
| Variables | Local declarations, initialization, assignment, block shadowing |
| Expressions | Arithmetic, comparisons, `!`, short-circuit `&&` / `||`, nested calls |
| Control flow | `if` / `else`, `while`, `do-while`, `for`, `return` |
| Functions | Typed parameters; `int`, `bool`, or `void` returns; direct recursion |
| Output | Literal-format `printf`: `%d`, `%i`, `%c`, `%s`, `%%`; byte-count return |
| Teaching tools | Tokens, typed AST, scoped symbol tables, pass tracing |
| Verification | Standalone golden cases and exact C11 execution comparisons |

Functions must be defined before calls; direct recursion is supported. An
`int main()` or `int main(void)` is required. Includes are virtual whitelisted
`<stdio.h>` and `<stdbool.h>` directives, placed before function definitions.

The broader study remains the roadmap. Global variables, `break` / `continue`,
prototypes and forward calls, mutual recursion, string variables and parameters,
a GUI, and a post-generation formatter are deferred. Pointers, memory allocation,
arrays, user-defined structures, floating point, bitwise operations, arbitrary
preprocessing, and system APIs are outside this core. Unsupported source is
diagnosed rather than silently translated.

Equivalence is verified for defined, terminating C executions: integer results
must fit the reference C `int`, divisors must be nonzero, variables must be
initialized before reads, and expressions must avoid unsequenced side effects.
There is no general definite-assignment or all-path return analysis. Non-void
helpers must return a value on paths used by the program. Python integers do not
emulate signed C overflow.

## Tests and teaching material

```sh
CMINUS_CC=gcc python -m pytest -q
```

CI tests Python 3.10 and 3.14 with GNU GCC and rejects skipped or expected-failure
tests. Local GCC-dependent tests skip if the selected compiler is unavailable.

- [Formal grammar and language rules](docs/grammar.md)
- [AST and binding contract](docs/ast_spec.md)
- [Compiler walkthrough](docs/walkthrough.md)
- [Test guide](tests/README.md)
- [Verification record](docs/verification.md)
