#include <stdio.h>
int mark(int n) { printf("%d", n); return n; }
int main(void) {
    int x = 0;
    int a = 2 && 7;
    int b = 0 || -3;
    int c = !5;
    int d = mark(0) && mark(9);
    int e = mark(2) || mark(9);
    if ((x = 3) && (x = x + 1)) printf(":%d %d %d %d\n", a, b, c, x);
    return 0;
}
