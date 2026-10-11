# Pointer scope and readable Python output

C-Minus supports pointers to integer and boolean variables, including pointer
declarations, address-of (`&`), dereferencing (`*`), updates through pointers,
and passing pointers to functions. This extends the original study's scope.

## Supported operations

- Local/global `int *` and `bool *` declarations and matching function parameters.
- Taking the address of a numeric variable and reading/writing its value.
- Copying or rebinding pointers while preserving aliases to the original value.
- Pointer equality for matching pointee types; literal `0` as null.
- Null/non-null conditions and short-circuit boolean operations.
- Global pointer initialization from an earlier global numeric address or `0`.
- Numeric conversions when storing through a pointer, including normalization
  of a boolean target to false/true.

Prototypes validate the exact pointee type: an `int *` parameter accepts an
`int *`, and a `bool *` parameter accepts a `bool *`. Numeric value arguments
retain the existing int/bool conversion rules. Functions return int/bool/void;
pointer return types are excluded from this extension.

```c
void increment(int *number) {
    *number = *number + 1;
}

int main(void) {
    int count = 5;
    int *pointer = &count;
    increment(pointer);
    return count;
}
```

The generated Python uses a small shared storage class:

```python
class Reference:
    def __init__(self, value):
        self.value = value


def increment(number):
    number.value = number.value + 1


def main():
    count = Reference(5)
    pointer = count
    increment(pointer)
    return count.value
```

Both `count` and `pointer` refer to the same storage, so either can observe the
update. Parameters passed by value get separate storage if their address is
taken inside the function. Rebinding a pointer parameter changes that parameter,
while writing its `.value` updates the referenced variable.

Only variables whose addresses are used are boxed. Ordinary scalar programs
keep direct names and assignments. Nested block shadowing uses short suffixes
such as `count_2`; unrelated functions can both use `number`. Assignment
expressions through pointers use a small `set_value` helper because Python's
assignment expression cannot target an attribute.

## Boundaries

Pointer arithmetic, pointer-to-pointer types, pointer returns, function pointers,
void pointers, casts, mutable buffers, arrays, allocation/free, and `%p` raw-memory
addresses are excluded. `<stdlib.h>` and arbitrary preprocessor macros remain
unsupported. Use literal `0` for null; the `NULL` macro is not expanded.

Verification covers initialized pointers referring to live numeric variables.
Null dereferences, uninitialized reads, and accesses after the C object's
lifetime ends have undefined C behavior and are outside the equivalence domain.
The Python storage objects model aliases; they do not emulate physical addresses.
These rules use the [C11 draft, sections 6.3.2.3 and 6.5.3.2](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).

## Try and inspect

```sh
cminus examples/pointers.c --run
cminus examples/pointers.c -o /tmp/pointers.py
python -I -S /tmp/pointers.py
cminus-check examples/pointers.c --cc gcc
```

The example prints `count=6 ready=1`. Its
[generated Python](../examples/generated/pointers.py) remains standalone.
Regression tests cover aliasing, rebinding, nullable comparisons, typed parameters,
numeric parameter copies, global references, nested scopes, loop jumps, and
address-taking during initialization.
