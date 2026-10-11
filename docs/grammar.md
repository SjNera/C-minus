# C-Minus working-core grammar

This grammar describes the implemented CLI core. Braces in the EBNF mean
repetition, brackets mean optional syntax, and quoted text denotes terminals.

```ebnf
program       = { include }, { function }, EOF ;
include       = "#include", ("<stdio.h>" | "<stdbool.h>") ;
function      = return_type, identifier, "(", [ parameters ], ")", block ;
return_type   = type | "void" ;
type          = "int" | "bool" ;
parameters    = "void" | parameter, { ",", parameter } ;
parameter     = type, identifier ;

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
double-quoted ASCII sequence with no physical newline. Supported escapes are
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
- Helpers must appear before callers. The function currently being checked is
  visible to itself, allowing direct recursion. Forward calls, prototypes, and
  mutual recursion are deferred. Call arity and argument types are checked.
- A void call may stand alone; its result cannot supply a value. Explicit return
  statements must match the enclosing function. All-path return analysis is
  deferred; falling off `main` returns zero.
- `printf` is built in and cannot be redefined. Its first argument must be a
  string literal. `%d`, `%i`, and `%c` accept int/bool; `%s` accepts a string
  literal. `%%` consumes no argument. Counts and types must match; widths,
  precision, and other format specifiers are rejected. Formats stop at `\0`.

## Target behavior

Division truncates toward zero without converting through floating point.
Remainder follows `a - b * trunc(a / b)`. Comparisons and logical operators
produce numeric 0/1, and `&&` / `||` preserve short-circuit evaluation. Assignments
used in expressions retain their value. `for` lowers to initialization plus a
`while` loop; `do-while` runs its body before testing the condition.

Every source binding receives a stable ID used to rename Python identifiers.
This preserves C block shadowing and avoids collisions with Python keywords,
builtins, and generated helpers. Only required runtime helpers are embedded.
`printf` writes bytes without an implicit newline and returns the byte count;
`%c` converts its integer to one byte, and `%s` stops at the first NUL.

Behavioral comparisons cover defined C executions within the reference compiler's
signed-int range. Overflow, division by zero, uninitialized reads, unsequenced
side effects, and non-void helper fallthrough are outside the verified domain.
