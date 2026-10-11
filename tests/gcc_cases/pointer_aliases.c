#include <stdio.h>
#include <stdbool.h>

int main(void) {
    int x = 5;
    int y = 9;
    int *p = &x;
    int *q = p;
    *p = 7;
    x = x + 1;
    *q = *q + 3;
    printf("shared %d %d\n", x, *p);

    p = &y;
    int result = (*p = (*q = 12));
    printf("rebound %d %d %d\n", x, y, result);
    printf("identity %d %d %d\n", p == &y, q == &x, p != q);

    bool present = p;
    p = 0;
    bool absent = p;
    printf("null %d %d %d %d %d\n", present, absent, !p, p == 0, &*p == 0);
    if (p && (*p = 99)) {
        printf("unexpected");
    }
    printf("unchanged %d %d\n", x, y);
    return 0;
}
