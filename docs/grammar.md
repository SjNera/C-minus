# C-Minus grammar

This grammar describes the implemented CLI language. Braces in the EBNF mean
repetition, brackets mean optional syntax, and quoted text denotes terminals.

```ebnf
program       = { include }, { top_level }, EOF ;
include       = "#include", ("<stdio.h>" | "<stdbool.h>") ;
top_level     = declaration | function | prototype ;
function      = return_type, identifier, "(", [ parameters ], ")", block ;
prototype     = return_type, identifier, "(", [ proto_params ], ")", ";" ;
return_type   = type | "void" ;
type          = "int" | "bool" ;
parameters    = "void" | parameter, { ",", parameter } ;
parameter     = type, identifier ;
proto_params  = "void" | proto_param, { ",", proto_param } ;
proto_param   = type, [ identifier ] ;

block         = "{", { declaration | statement }, "}" ;
declaration   = type, identifier, [ "=", expression ], ";" ;
statement     = block
              | ";"
              | expression, ";"
              | "if", "(", expression, ")", statement, [ "else", statement ]
              | "while", "(", expression, ")", statement
              | "do", statement, "while", "(", expression, ")", ";"
              | "for", "(", for_init, [ expression ], ";",
                [ expression ], ")", statement
              | "break", ";"
              | "continue", ";"
              | "return", [ expression ], ";" ;
for_init      = declaration | [ expression ], ";" ;

expression    = logical_or, [ "=", expression ] ;
logical_or    = logical_and, { "||", logical_and } ;
logical_and   = equality, { "&&", equality } ;
equality      = comparison, { ("==" | "!="), comparison } ;
comparison    = additive, { ("<" | "<=" | ">" | ">="), additive } ;
additive      = product, { ("+" | "-"), product } ;
product       = unary, { ("*" | "/" | "%"), unary } ;
unary         = ("-" | "!"), unary | primary ;
primary       = integer | boolean | string
              | identifier, [ "(", [ arguments ], ")" ]
              | "(", expression, ")" ;
arguments     = expression, { ",", expression } ;

identifier    = (letter | "_"), { letter | digit | "_" } ;
integer       = "0" | nonzero_digit, { digit } ;
boolean       = "true" | "false" ;
```

Identifiers use ASCII letters and cannot be reserved keywords. A string is a
double-quoted UTF-8 sequence with no physical newline. Supported escapes are
`\n`, `\r`, `\t`, `\a`, `\b`, `\f`, `\v`, `\0`, `\\`, `\"`, `\'`, and `\?`.
Other octal, hexadecimal, Unicode, and line-continuation escapes are rejected.
Negative integers use unary `-`; integer suffixes and nondecimal literals are
excluded. Adjacent string concatenation and character literals are unsupported.

The lexer discards whitespace, `//` comments, and `/* ... */` comments, preserving
one-based line and column positions. CRLF and CR line endings are normalized.
Each token stores its class, original lexeme, line, and column; EOF is explicit.
Virtual includes must occupy their own source line, with optional whitespace and
a trailing line comment or a single same-line block comment. Whitespace around
`#`, `include`, and the header is accepted. No headers are actually read.

## Parsing rules

The parser uses recursive descent and precedence levels, without rewriting
source text. Binary operators associate left; assignment associates right. An
assignment's left side must resolve syntactically to an identifier. An `else`
binds to the nearest unmatched `if`; `else if` uses an `If` inside the else branch.
Declarations are block items or `for` initializers, never an unbraced branch body.
An empty statement is represented by an empty `Block`.

## Semantic rules

- Exactly one `main` definition must return `int` and take no parameters.
- Variables and parameters have type `int` or `bool`; function returns may also
  be `void`. Int/bool conversions apply at declarations, assignments, calls, and
  returns. Conditions require int/bool. Strings are literals used for output.
- A function body shares a scope with its parameters. Nested blocks and `for`
  headers introduce scopes. A declaration becomes visible at its declarator;
  reads of that binding in its own initializer are rejected, including shadowing
  an outer declaration with the same name. Assignment targets are checked as
  writes. General definite-assignment analysis is deferred.
- Names cannot be redeclared within one scope; nested shadowing is allowed.
  Calls resolve the nearest binding, so a local variable can hide a function.
- Global variables have numeric constant initializers, using literals and the
  supported unary/binary operators. Uninitialized globals start at zero or
  false. Identifiers, assignments, and calls are not constant initializers.
  Constant evaluation preserves short-circuit behavior and diagnoses evaluated
  division by zero. Global variables must be declared before a function that
  refers to them. Local declarations may shadow them.
- A function definition or prototype must precede each call. The current
  function is visible to itself. Prototypes permit forward calls and mutual
  recursion; used functions require a definition somewhere in the program.
  Matching prototypes share a binding; conflicting signatures and duplicate
  definitions are rejected. Parameter names are optional in prototypes, required
  in definitions, and do not affect signature compatibility. Both `()` and
  `(void)` mean no parameters in this subset. Call arity and types are checked.
- A void call may stand alone; its result cannot supply a value. Explicit return
  statements must match the enclosing function. All-path return analysis is
  deferred; falling off `main` returns zero.
- `break` and `continue` require an enclosing loop body, even in unreachable
  branches. Loop context is local to each function; calling a helper from a loop
  does not permit a jump inside that helper to affect the caller's loop.
- `printf` is built in and cannot be redefined. Its first argument must be a
  string literal. `%d`, `%i`, and `%c` accept int/bool; `%s` accepts a string
  literal. `%%` consumes no argument. Counts and types must match. Formats stop
  at `\0`; unsupported conversions and combinations receive a diagnostic.

## Supported printf formats

The shared compile-time/runtime format parser accepts
`%[flags][width][.precision]conversion`:

| Conversion | Flags | Width | Precision |
| --- | --- | --- | --- |
| `d`, `i` | `-`, `+`, space, `0` | Decimal digits or `*` | Decimal digits or `*` |
| `s` | `-` | Decimal digits or `*` | Decimal digits or `*` |
| `c` | `-` | Decimal digits or `*` | Excluded |
| `%` | Excluded | Excluded | Excluded |

A bare precision dot means zero. Each `*` consumes an int/bool argument before
the conversion's value. Negative dynamic width requests left alignment;
negative dynamic precision is omitted. Integer precision disables zero padding
by width. String precision limits bytes, including a possible partial UTF-8
sequence. These mappings follow the
[C11 draft, section 7.21.6.1](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).
Length modifiers, floating-point conversions, and other conversions are excluded.

## Target behavior

Division truncates toward zero without converting through floating point.
Remainder follows `a - b * trunc(a / b)`. Comparisons and logical operators
produce numeric 0/1, and `&&` / `||` preserve short-circuit evaluation. Assignments
used in expressions retain their value. `for` lowers to initialization plus a
`while` loop; `do-while` runs its body before testing the condition.

`break` exits the innermost loop and skips its remaining body, step, and condition
checks. `continue` skips the remaining body of that loop: `while` retests its
condition, `for` executes its step before retesting, and `do-while` tests its
condition before another iteration. These rules follow the
[C11 draft, sections 6.8.5 and 6.8.6.2–3](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).
The generator tracks a loop stack and emits the necessary continuation operation
before Python's `continue`; nested jumps use only the nearest loop's operation.

Every source binding receives a stable ID used to rename Python identifiers.
This preserves C block shadowing and avoids collisions with Python keywords,
builtins, and generated helpers. Global writes produce Python `global`
declarations for their resolved bindings; local shadowing remains separate.
Only required runtime helpers are embedded.
`printf` writes bytes without an implicit newline and returns the byte count;
`%c` converts its integer to one byte, and `%s` stops at the first NUL.

The final pass formats Python for the Python 3.10 target at 79 columns, following
[PEP 8's line-length guidance](https://peps.python.org/pep-0008/#maximum-line-length).
Long string literals are split into adjacent Python literals without changing
their value. The formatter checks that the Python AST is unchanged and that the
result parses and compiles before the CLI writes an output file.

Behavioral comparisons cover defined C executions within the reference compiler's
signed-int range. Overflow, division by zero, uninitialized reads, unsequenced
side effects, and non-void helper fallthrough are outside the verified domain.
