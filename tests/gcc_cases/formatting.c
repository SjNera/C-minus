#include <stdio.h>
#include <stdbool.h>
int main(void) {
    int count = printf("%%%d %i %s %c\n", true, -3, "ok", 321);
    printf("count=%d|", count);
    printf("tail");
    return 7;
}
