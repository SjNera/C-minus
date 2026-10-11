#include <stdio.h>
int check(int n) { printf("%d", n); return n < 3; }
int main(void) {
    int n = 0;
    while (check(n)) n = n + 1;
    do { n = n - 1; } while (check(n) && n > 1);
    for (n = 0; check(n); n = n + 1) ;
    printf(" %d\n", n);
    return 0;
}
