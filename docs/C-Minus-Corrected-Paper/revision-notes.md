# Revision notes

The corrected paper retains the supplied covers and Chapters 3 and 4. Technical claims were checked against the local implementation of C-Minus 0.2.0 and its dated verification record.

## Corrections

- Corrected the BOOL, IDENTIFIER, and INT token patterns.
- Used the lexer’s real token types: `INT`, `=`, and `;`.
- Separated numeric/void function returns from pointer object and parameter types in the accepted grammar.
- Clarified declarations at global scope, in blocks, and in `for` initializers.
- Replaced illustrative class and constant names with names actually present in the code.
- Removed claims about structural pattern matching, diagnostic queues, and `None` representing the semantic void type.
- Identified `@dataclass` as a decorator, not a data type.
- Distinguished Black’s formatting pass from pycodestyle’s test-time checks.
- Explained reference storage allocation and pointer parameters accurately; avoided claiming memory-safety guarantees.
- Described normal and `continue` loop updates, including the absence of a step on `break`/`return`.
- Distinguished direct print/f-string output from byte-count and advanced-format helpers.
- Distinguished positioned compiler diagnostics from Python runtime exceptions.
- Removed the unsupported performance-benchmark claim and distinguished configured CI from recorded local runs.
- Completed the AST examples, symbol table design, error handling, flowchart, and optional sequence diagram.
- Added source and CLI-output images with complete transcripts. Images are rendered captures of real text, not desktop screenshots.

## Administrative details to confirm

- CS 200 was used consistently because it appears on the assignment cover. The supplied title page previously used CS 002.
- The date was written as 11 October 2026, consistent with the supplied October 2026 title page.
- Group number and section remain blank because they were not supplied.

## Format

The paper is editable Markdown. Mermaid blocks contain the architecture, flowchart, and sequence diagrams. The `assets` folder holds PNG figures and actual-output transcripts. Keep that folder alongside the paper so image links resolve.

Word export was unavailable because the documents skill requires the managed document runtime, which is not provisioned in this session.
