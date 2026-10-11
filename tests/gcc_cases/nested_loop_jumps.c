#include <stdio.h>

int check(int n) {
    printf("C%d ", n);
    return n < 3;
}

int main(void) {
    int outer = 0;
    int total = 0;
    do {
        outer = outer + 1;
        for (int j = 0; j < 4; j = j + 1) {
            if (j == 1) continue;
            int k = 0;
            while (k < 4) {
                k = k + 1;
                if (k == 1) continue;
                if (k == 3) break;
                total = total + outer * 100 + j * 10 + k;
            }
            if (j == 2) break;
        }
        if (outer == 1) continue;
        if (outer == 2) break;
    } while (check(outer));
    printf("total=%d outer=%d\n", total, outer);
    return 0;
}
