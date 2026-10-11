#include <stdio.h>
#include <stdbool.h>
bool positive(int value) { return value; }
int count(bool flag) { return flag + 4; }
int fact(int n) { if (n <= 1) return 1; return n * fact(n - 1); }
void show(int n) { printf("F=%d bool=%d\n", fact(n), count(positive(-2))); return; }
int main(void) { show(5); return 0; }
