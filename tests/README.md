# Running the tests

From the repository root, install the package and pytest into a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e . 'pytest>=8.0'
.venv/bin/python -m pytest -q -rx
```

The active tests cover AST and token contracts, error diagnostics, semantic
analysis, symbol tables, package metadata, and CLI entry points. Semantic tests
use hand-built ASTs so they run independently of the unfinished lexer and parser.

Lexer, parser, code generator, runtime, and example integration tests are marked
`xfail(raises=NotImplementedError, strict=True)` while those stages are unfinished.
Only `NotImplementedError` counts as an expected failure; incorrect results and
other exceptions fail normally. A passing marked test fails as `XPASS`, signalling
that its marker should be removed when the corresponding work is complete. Split
module-wide markers into individual markers if only part of a stage is ready.

Run only the implemented behavior with:

```sh
.venv/bin/python -m pytest -q -m 'not xfail'
```

The pending lexer tests avoid assumptions about token type names and EOF tokens.
Empty GUI and extras modules have no behavior to test yet; the gcc checker has an
entry-point smoke test.
