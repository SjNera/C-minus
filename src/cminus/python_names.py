"""Readable Python names that preserve C's separate lexical bindings."""

import keyword

from cminus.semantic_analyser import SymbolTable

RESERVED = {
    "Reference",
    "set_value",
    "write",
    "printf",
    "sys",
    "c_div",
    "c_mod",
    "int",
    "bool",
    "print",
    "str",
    "bytes",
    "bytearray",
    "len",
    "max",
    "abs",
    "isinstance",
    "format",
    "ValueError",
    "SystemExit",
    "__name__",
}


def readable_names(symbols: SymbolTable) -> dict[int, str]:
    names = {}

    def allocate(symbol, used):
        base = symbol.name[:32]
        if keyword.iskeyword(base):
            base += "_"
        name = base
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        names[symbol.binding_id] = name

    global_names = set(RESERVED)
    for symbol in symbols.global_scope.symbols.values():
        if symbol.builtin:
            names[symbol.binding_id] = "printf"
        else:
            allocate(symbol, global_names)
    functions = {}
    for scope in symbols.all_scopes[1:]:
        owner = scope
        while owner.parent is not symbols.global_scope:
            owner = owner.parent
        used = functions.setdefault(id(owner), set(global_names))
        for symbol in scope.symbols.values():
            allocate(symbol, used)
    return names
