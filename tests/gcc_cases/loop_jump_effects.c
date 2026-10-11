#include <stdio.h>

int step(int n) {
    printf("S%d ", n);
    return n + 1;
}

int check(int n) {
    printf("C%d ", n);
    return n < 3;
}

int main(void) {
    for (int i = 0; check(i); i = step(i)) {
        if (i == 0) {
            int i = 50;
            continue;
        }
        if (i == 2) break;
        printf("B%d ", i);
    }
    printf("|");

    int n = 0;
    do {
        n = n + 1;
        if (n == 1) {
            int n = 99;
            continue;
        }
        if (n == 3) continue;
        printf("D%d ", n);
    } while (check(n));
    do break; while (check(9));
    printf("|");

    int q = 0;
    for (; q < 3; printf("V%d ", q = q + 1)) continue;
    printf("\n");
    return 0;
}
