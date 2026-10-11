# Study requirements audit

The required CLI features in the supplied study are implemented for the language
defined in [the grammar](grammar.md). This is an educational C-subset transpiler;
its verification applies to supported programs with defined C behavior.

| Study requirement | Implementation | Verification evidence |
| --- | --- | --- |
| Define a supported language and exclusions | Formal grammar, typed AST, positioned rejection of excluded syntax | `docs/grammar.md`, `tests/test_core_pipeline.py` |
| Lexical analysis, comments, token metadata | Shared tokens with class, lexeme, line and column; both C comment forms | `tests/test_lexer.py`, token inspection |
| Deterministic syntax analysis and AST | Recursive descent, explicit precedence, shared dataclasses | `tests/test_parser.py`, `docs/ast_spec.md` |
| Scoped symbol tables and semantic checks | Global, function, block and loop scopes; declaration, type, signature and return checks | `tests/test_semantic.py`, symbol inspection |
| Integer, boolean and string literals | Numeric arithmetic/conversions and UTF-8 literal output | `arithmetic.c`, `byte_output.c`, `utf8_strings.c` |
| Global and local variables | Constant or zero global initialization, shared writes, unique bindings for shadowing | `globals.c`, `global_constants.c`, `bindings.c` |
| Expressions and evaluation behavior | C integer division/remainder, numeric logical results, short-circuiting, nested calls and assignment expressions | `arithmetic.c`, `short_circuit.c`, `functions.c` |
| Branches and loops | `if`, `else if`, `else`, `while`, `do-while`, and `for` | `control_flow.c`, `loop_conditions.c` |
| Break, continue and return | Innermost loop jumps, correct continuation step/guard, typed returns | `tests/test_loop_jumps.py`, three loop-jump fixtures |
| Functions and signature validation | Typed parameters, numeric/void returns, matching prototypes, forward calls and direct/mutual recursion | `prototypes.c`, `functions.c`, `tests/test_remaining_features.py` |
| Executable Python generation | Python AST construction, embedded helpers, binding-aware global declarations | Standalone runs with `-I -S` under Python 3.10 and 3.14 |
| Format-string output | Compile-time format/type checks; `%d`, `%i`, `%s`, `%c`, `%%`, flags, width and precision | `formatting.c`, `printf_fields.c`, `utf8_strings.c` |
| Readable Python formatting | Black pass at 79 columns, exact AST comparison, syntax validation | pycodestyle checks for all 21 valid fixtures/examples; long-literal tests |
| Informative errors and introspection | Filename, line, column, source caret; token/AST/symbol dumps and five-pass tracing | `tests/test_core_cli.py`, `tests/test_remaining_features.py` |
| GCC-equivalence testing | Compile original C11 with explicit UTF-8 encodings; compare stdout bytes, stderr bytes and exit status | [Verification record](verification.md), GNU GCC tests and CI configuration |
| Practical teaching demonstration | Installed CLI, reusable API, four examples, phase walkthrough | [Walkthrough](walkthrough.md), `tests/test_examples.py` |

The implementation retains the agreed CLI workflow and literal-only strings.
A GUI and a custom string-variable type were optional extensions, rather than
requirements of the supplied subset. Pointer-backed C strings, arrays, memory
allocation, structs/unions/enums/typedefs, floating point, bitwise operations,
arbitrary preprocessing, low-level APIs, and native or bytecode targets remain
excluded as documented in the project scope.

Function prototypes use fixed parameter lists: `()` and `(void)` both mean no
parameters here. Global initializers must be numeric constant expressions.
General definite-assignment and all-path return analysis are not implemented;
verification uses initialized reads and returning paths in non-void helpers.
Signed integer overflow and unsequenced side effects are outside the verified
domain. These boundaries prevent the subset from implying full ISO C support.

The tests demonstrate behavioral preservation for the supported cases. They do
not quantify migration time savings or student learning outcomes; those claims
would require separate user studies or benchmarks.
