# C-Minus: From C to Python

A working educational source-to-source compiler for a defined subset of C. The
pipeline tokenizes source, builds a shared AST, checks types and lexical scopes,
and generates formatted, standalone Python 3.10+ programs.

## Install the CLI

Requires Python 3.10 or newer. From the directory containing `pyproject.toml`:

```sh
pipx install .
pipx ensurepath
cminus --version
cminus-check --version
```

This installs both commands in an isolated application environment. After
`ensurepath`, open a new terminal if the commands are not yet on your PATH.
No project virtual-environment activation is needed. See the
[installation guide](docs/installation.md) for pipx setup, wheel installation,
upgrades, removal, and distribution builds. The
[Python Packaging User Guide](https://packaging.python.org/en/latest/guides/installing-stand-alone-command-line-tools/)
explains how pipx exposes CLI commands.

## Development setup

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
cminus --version
```

The compiler uses Black to format its output. Development dependencies provide
pytest and pycodestyle. Generated programs use only Python's standard library.
A C11 compiler is needed for equivalence checks.

## Translate, run, and inspect

```sh
cminus examples/hello.c -o /tmp/hello.py
python -I -S /tmp/hello.py
cminus examples/factorial.c --run
cminus examples/loop_control.c --run
cminus examples/globals_and_recursion.c --run
cminus examples/pointers.c --run
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

| Area | Supported behavior |
| --- | --- |
| Values | Decimal `int`, `bool`, and UTF-8 string literals |
| Variables | Global and local declarations, initialization, assignment, block shadowing |
| Pointers | `int*` and `bool*`, `&`, dereferencing, shared updates and typed function parameters |
| Expressions | Arithmetic, comparisons, `!`, short-circuit `&&` / `||`, nested calls |
| Control flow | `if` / `else`, `while`, `do-while`, `for`, `break`, `continue`, `return` |
| Functions | Typed parameters, prototypes, forward calls, direct and mutual recursion |
| Output | Literal-format `printf`: `%d`, `%i`, `%c`, `%s`, `%%`, widths and precision |
| Formatting | Automatic Black formatting at 79 columns, with AST equivalence checks |
| Readability | Original names where possible, direct assignments, simple `print`/f-strings, compact reference storage |
| Teaching tools | Tokens, typed AST, scoped symbol tables, pass tracing |
| Verification | Standalone golden cases and exact C11 execution comparisons |

Functions must be declared before calls: either a definition or a matching
prototype suffices. Used functions must have a definition in the same program.
Returns may be `int`, `bool`, or `void`; an `int main()` or `int main(void)`
definition is required. Global numeric variables default to zero, or accept a
constant numeric initializer. Global pointers default to null, or accept the
address of an earlier global numeric variable. Includes are virtual whitelisted
`<stdio.h>` and `<stdbool.h>` directives, placed before top-level declarations.

`printf` validates format arguments at compile time. Numeric conversions accept
`-`, `+`, space, and `0` flags, widths, and precision; `%s` accepts width and
precision, and `%c` accepts width. Dynamic `*` fields consume numeric arguments.
Output preserves UTF-8 bytes, NUL termination, and the C byte-count return value.
Common formats become Python `print` calls and f-strings. Calls whose return value
is used retain a small output helper. Complex formats use a pre-parsed format;
generated programs do not include a runtime format parser.

Pointers refer to shared `Reference` objects. Taking `&count` preserves the same
object; `*pointer` becomes `pointer.value`. Updating either alias changes the
same value. Ordinary variables keep direct Python assignments; storage is boxed
only when its address is used. See [pointer scope and translation](docs/pointers.md)
and the runnable [generated example](examples/generated/pointers.py).

`break` and `continue` target the innermost enclosing loop. A `for` continuation
runs its step expression, and a `do-while` continuation tests its condition.
Both keywords receive a semantic diagnostic when used outside a loop.

The required CLI features from the study are implemented for this defined subset.
The [requirements audit](docs/requirements.md) maps them to implementation and
verification evidence. Strings remain literals; string variables and parameters
and a GUI are optional extensions. Pointer arithmetic, multiple pointer levels,
pointer returns, function/void pointers, raw-address output, memory allocation,
arrays, user-defined structures, floating point, bitwise operations, arbitrary
preprocessing, and system APIs are excluded. Unsupported source receives a
positioned diagnostic.

Equivalence is verified for defined, terminating C executions: integer results
must fit the reference C `int`, divisors must be nonzero, variables must be
initialized before reads, and expressions must avoid unsequenced side effects.
Pointers must refer to live variables when dereferenced.
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
- [Installation and packaging](docs/installation.md)
- [AST and binding contract](docs/ast_spec.md)
- [Compiler walkthrough](docs/walkthrough.md)
- [Study requirements audit](docs/requirements.md)
- [Test guide](tests/README.md)
- [Verification record](docs/verification.md)
