# Shared AST and binding contract

The canonical definitions are in `src/cminus/ast_nodes.py`. The parser, semantic
analyser, and generator all use these dataclasses; they do not define private ASTs.

Every `Node` has keyword-only `line`, `column`, and `binding_id` metadata. Source
positions are one-based; manually constructed test nodes may default to zero.
Every `Expr` also has keyword-only `resolved_type`, initially `None`. Types are
the strings `int`, `bool`, `string`, and `void`.

| Node | Structural fields |
| --- | --- |
| `Program` | ordered `declarations`, `includes` |
| `FunctionDecl` | `return_type`, `name`, `params`, `body` |
| `FunctionPrototype` | `return_type`, `name`, `params` |
| `Param` | `type_name`, `name` |
| `Block` | `statements` |
| `VarDecl` | `type_name`, `name`, optional `init` |
| `ExprStmt` | `expr` |
| `If` | `condition`, `then_branch`, optional `else_branch` |
| `While` | `condition`, `body` |
| `DoWhile` | `body`, `condition` |
| `For` | optional `init`, `condition`, `step`; `body` |
| `Return` | optional `value` |
| `Break`, `Continue` | no structural fields; inherited source metadata |
| `IntLiteral`, `BoolLiteral`, `StringLiteral` | `value` |
| `Identifier` | `name` |
| `Assign` | identifier `target`, `value` |
| `BinaryOp` | `op`, `left`, `right` |
| `UnaryOp` | `op`, `operand` |
| `Call` | `callee`, `args` |

`StringLiteral.value` contains decoded text. Includes are header names such as
`stdio.h`. `For.init` is `VarDecl`, `ExprStmt`, or `None`.
`Program.declarations` preserves source order across `VarDecl`,
`FunctionPrototype`, and `FunctionDecl` nodes. A `VarDecl` at program level is a
global variable. `Program.functions` and `Program.globals` are filtered views of
definitions and global variables. An unnamed prototype parameter has `name=""`.
Loop jumps are statements, validated against the enclosing loop context and
generated for the innermost loop.

## Phase contracts

1. `lexer_analyser.tokenize(source)` returns shared `Token` instances and EOF,
   raising `LexicalError` for unsupported or malformed input.
2. `parser.parse(tokens)` returns `Program`, raising `ParseError` for syntax.
3. `semantic_analyser.analyse(program)` annotates the AST and returns a
   `SymbolTable`, raising `SemanticError` for invalid bindings or types.
4. `code_generator.generate(program, symbols)` requires the validated AST and
   its matching symbol table, and returns standalone Python source.
5. `extras.formatter.format_source(python_source)` formats for Python 3.10 at
   79 columns and validates unchanged AST semantics and executable syntax.

`compiler.compile_source()` runs these phases and returns a `Compilation`
containing `tokens`, `program`, `symbols`, and `python_source`.

The semantic pass gives each declaration a deterministic binding ID and records
it in `SymbolTable.bindings`. Function declarations, parameters, variables,
identifier references, assignment targets, and calls retain the resolved ID.
Compound expressions receive a type; they do not all have their own binding.
The generator uses these IDs rather than repeating name lookup.

Symbols include declaration kind, type, location, and function parameters.
Function symbols record `defined`; compatible prototypes and their definition
share one binding. Variable symbols record `is_global`; global `initial_value`
contains the normalized constant or zero default used in code generation.
Scopes retain parent links and declarations in creation order. Parameters and
the outer function block share a scope; nested blocks and loops add child scopes.
The global scope holds functions, builtin `printf`, and global variables.
Predeclaring symbols supports signature checks and mutual recursion, while
source-order visibility checks still reject uses before a declaration.

All source phases raise subclasses of `CMinusError`. CLI boundaries render the
diagnostic; compiler modules do not print it. Introspection uses deterministic
text representations of the actual shared objects, including semantic metadata.
