# Running the tests

From the repository root, install the package and pytest into a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e . 'pytest>=8.0'
CMINUS_CC=gcc .venv/bin/python -m pytest -q
```

The suite covers shared contracts, all four compiler phases, runtime helpers,
positioned diagnostics, installed entry points, output-file preservation, and
standalone execution from another directory. Stage tests are active; there are
no unfinished-stage xfail markers.

`test_core_pipeline.py` runs nine golden C fixtures from `gcc_cases/`, then
compares their generated Python with actual C11 executions. It also checks exact
observable differences, missing compilers, compilation failure, and timeouts at
every subprocess stage. `test_core_cli.py` checks inspection streams, phase
failures, output files, and checker status codes. Existing semantic unit tests
still use hand-built ASTs to test type and scope rules independently of parsing.

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

The C compiler defaults to `gcc`; set `CMINUS_CC` to another executable. On macOS,
select a versioned GNU executable when `gcc --version` reports Apple Clang. Local
compiler-dependent tests skip if that executable is absent. CI requires GNU GCC
and checks the JUnit report for zero skips and zero expected failures on Python
3.10 and 3.14. Missing-tool and timeout diagnostics remain testable locally.

Reference fixtures use defined, terminating C behavior. Add both a standalone
golden expectation and a C comparison when extending supported behavior. Keep
unsupported-feature cases as positioned diagnostics instead of xfails.
