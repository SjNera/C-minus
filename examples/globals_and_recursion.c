#include <stdio.h>
#include <stdbool.h>

int calls;
bool even(int);
bool odd(int);

int main(void) {
    bool result = even(6);
    printf("even(6)=%d calls=%d\n", result, calls);
    return 0;
}

bool even(int n) {
    calls = calls + 1;
    if (n == 0) return true;
    return odd(n - 1);
}

bool odd(int n) {
    calls = calls + 1;
    if (n == 0) return false;
    return even(n - 1);
}
