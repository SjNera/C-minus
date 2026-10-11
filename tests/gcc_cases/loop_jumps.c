#include <stdio.h>

int main(void) {
    int i = 0;
    int sum = 0;
    while (i < 8) {
        i = i + 1;
        if (i == 2) continue;
        if (i == 5) break;
        sum = sum + i;
    }
    printf("while %d %d\n", i, sum);

    sum = 0;
    for (i = 0; i < 8; i = i + 1) {
        if (i == 1 || i == 3) continue;
        if (i == 6) break;
        sum = sum + i;
    }
    printf("for %d %d\n", i, sum);

    i = 0;
    sum = 0;
    do {
        i = i + 1;
        if (i == 2) continue;
        if (i == 5) break;
        sum = sum + i;
    } while (i < 8);
    printf("do %d %d\n", i, sum);

    for (;;) { break; }
    int trips = 0;
    for (; trips < 3;) {
        trips = trips + 1;
        continue;
    }
    while (1) break;
    do break; while (printf("BAD") > 0);
    printf("empty %d\n", trips);
    return 0;
}
