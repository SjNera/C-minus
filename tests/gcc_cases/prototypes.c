#include <stdio.h>
#include <stdbool.h>

bool odd(int);
bool even(int value);
int add(int left, int right);
int add(int, int);

int main(void) {
    printf("%d %d %d\n", odd(5), even(8), add(2, 3));
    return 0;
}

bool odd(int n) {
    if (n == 0) return false;
    return even(n - 1);
}

bool even(int n) {
    if (n == 0) return true;
    return odd(n - 1);
}

int add(int a, int b) { return a + b; }
