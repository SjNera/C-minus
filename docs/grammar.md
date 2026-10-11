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
object_type   = type, [ "*" ] ;
parameters    = "void" | parameter, { ",", parameter } ;
parameter     = object_type, identifier ;
proto_params  = "void" | proto_param, { ",", proto_param } ;
proto_param   = object_type, [ identifier ] ;

block         = "{", { declaration | statement }, "}" ;
declaration   = object_type, identifier, [ "=", expression ], ";" ;
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
unary         = ("-" | "!" | "&" | "*"), unary | primary ;
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
assignment's left side must be an identifier or unary dereference. An `else`
binds to the nearest unmatched `if`; `else if` uses an `If` inside the else branch.
Declarations are block items or `for` initializers, never an unbraced branch body.
An empty statement is represented by an empty `Block`.

## Semantic rules

- Exactly one `main` definition must return `int` and take no parameters.
- Variables and parameters have type `int`, `bool`, `int*`, or `bool*`;
  function returns are `int`, `bool`, or `void`. Int/bool conversions apply at
  declarations, assignments, calls, and returns. Conditions accept numeric or
  pointer values. Strings are literals used for output.
- `&variable` takes the address of an int/bool variable; `*pointer` reads or
  updates the referenced variable. Pointer assignments and arguments require
  the same pointed-to type, or the integer literal `0` for a null pointer.
  Matching pointers support `==` and `!=`, including comparison with `0`.
  `&*pointer` preserves the pointer without reading its referenced value.
  Pointer arithmetic, ordering, returns, multiple indirection, and void or
  function pointers are excluded. See [the pointer scope](pointers.md).
- A function body shares a scope with its parameters. Nested blocks and `for`
  headers introduce scopes. A declaration becomes visible at its declarator;
  reads of that binding in its own initializer are rejected, including shadowing
  an outer declaration with the same name. Taking its address is permitted.
  Assignment targets are checked as writes. General definite-assignment analysis
  is deferred.
- Names cannot be redeclared within one scope; nested shadowing is allowed.
  Calls resolve the nearest binding, so a local variable can hide a function.
- Numeric globals have constant initializers, using literals and the supported
  unary/binary operators. Uninitialized globals start at zero or false; global
  pointers start null. A global pointer initializer is `0` or the address of an
  earlier global int/bool variable. Identifiers, assignments, and calls are not
  numeric constant initializers.
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

Every source binding receives a stable semantic ID. Generated Python retains
the C name when possible, adding a suffix only for shadowing, reserved names,
or long identifiers. Variables whose address is taken use a small `Reference`
object; direct accesses and dereferencing use its `.value` attribute. Pointer
variables share these objects. Global writes produce Python `global`
declarations when the binding itself changes; shared-object updates need none.

Ordinary assignments use `name = value`; conversions appear only when a type
changes. Common `printf` statements become `print()` and f-strings. Cases that
need a byte-count return use a small writer, while advanced formats use a byte
formatter with the format parsed at compile time. Only required helpers are
embedded. Output preserves UTF-8 bytes, explicit newlines, and the byte count;
`%c` converts its integer to one byte, and `%s` stops at the first NUL.

The final pass formats Python for the Python 3.10 target at 79 columns, following
[PEP 8's line-length guidance](https://peps.python.org/pep-0008/#maximum-line-length).
Long string literals are split into adjacent Python literals without changing
their value. The formatter checks that the Python AST is unchanged and that the
result parses and compiles before the CLI writes an output file.

Behavioral comparisons cover defined C executions within the reference compiler's
signed-int range. Overflow, division by zero, uninitialized reads, unsequenced
side effects, null/dangling pointer access, and non-void helper fallthrough are
outside the verified domain.
