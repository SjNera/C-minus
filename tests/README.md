# Running the tests

From the repository root, install the package and test tools in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
CMINUS_CC=gcc .venv/bin/python -m pytest -q
```

The suite covers shared contracts, all five compiler/formatting passes, runtime helpers,
positioned diagnostics, installed entry points, output-file preservation, and
standalone execution from another directory. Stage tests are active; there are
no unfinished-stage xfail markers.

`test_core_pipeline.py` runs seventeen original golden C fixtures from
`gcc_cases/`, then compares their generated Python with actual C11 executions.
`test_pointers_and_readability.py` adds five pointer fixtures, covering aliases,
typed parameters, global references, loop updates, and address-taking during
initialization. It also checks unsupported pointer diagnostics, readable names,
helper selection, f-strings, byte counts, and UTF-8 output. The core tests check exact
observable differences, missing compilers, compilation failure, and timeouts at
every subprocess stage. `test_core_cli.py` checks inspection streams, phase
failures, output files, and checker status codes. Existing semantic unit tests
still use hand-built ASTs to test type and scope rules independently of parsing.
`test_loop_jumps.py` verifies source positions, illegal jumps, parser errors,
semantic state recovery, and all nine nested pairs of loop types against C.
`test_remaining_features.py` checks global initializers and visibility, prototype
compatibility and definitions, rich format diagnostics, and formatter failure
handling. It verifies all twenty-two fixtures and five valid examples with
pycodestyle at 79 columns, compares raw and formatted Python ASTs, and checks
formatting idempotence. It also covers long escaped strings and long global names.

| Fixture | Behavior |
| --- | --- |
| `arithmetic.c` | Division toward zero and signed remainder |
| `control_flow.c` | Branches and all three loop forms |
| `short_circuit.c` | Skipped calls, assignments, logical 0/1 results |
| `functions.c` | Direct recursion and typed call/return conversions |
| `formatting.c` | Output formats, byte count, exact whitespace, exit 7 |
| `byte_output.c` | Raw non-UTF-8 `%c` byte and NUL truncation |
| `bindings.c` | Shadowing, Python keywords, chained assignments |
| `empty.c` | Empty bodies and implicit main return |
| `loop_conditions.c` | Calls repeated on every loop-condition test |
| `loop_jumps.c` | Break/continue in every loop form and empty for headers |
| `loop_jump_effects.c` | Step/condition side effects, shadowing, and skipped tails |
| `nested_loop_jumps.c` | Jumps affect the nearest enclosing loop |
| `globals.c` | Zero defaults, shared writes, local shadowing, continuation writes |
| `global_constants.c` | Constant arithmetic, conversions, short-circuit evaluation |
| `prototypes.c` | Forward calls, compatible prototypes, mutual recursion |
| `printf_fields.c` | Flags, widths, precision, dynamic fields, byte-limited strings |
| `utf8_strings.c` | UTF-8 output bytes, byte counts, string padding and precision |
| `pointer_aliases.c` | Shared writes, pointer reassignment, identity, and null guards |
| `pointer_functions.c` | Typed pointer parameters, recursion, swapping, boolean stores |
| `pointer_globals.c` | Global references, defaults, shared writes, and local shadowing |
| `pointer_loops.c` | Indirect updates in loop steps and continuations, scope and lifetimes |
| `pointer_initialization.c` | Own address during initialization and indirect initialization |

The C compiler defaults to `gcc`; set `CMINUS_CC` to another executable. On macOS,
select a versioned GNU executable when `gcc --version` reports Apple Clang. Local
compiler-dependent tests skip if that executable is absent. CI requires GNU GCC
and checks the JUnit report for zero skips and zero expected failures on Python
3.10 and 3.14. Missing-tool and timeout diagnostics remain testable locally.

Reference fixtures use defined, terminating C behavior. Add both a standalone
golden expectation and a C comparison when extending supported behavior. Keep
unsupported-feature cases as positioned diagnostics instead of xfails.

Distribution checks run separately from the editable-install unit tests. CI
builds the source archive and wheel, validates their metadata with Twine, installs
the wheel in a fresh virtual environment, and runs `tools/check_installation.py`
on Python 3.10 and 3.14. This checks command discovery, versions, translation,
execution, diagnostics, and C equivalence without importing the source checkout.
See the [installation guide](../docs/installation.md) to reproduce these checks.
