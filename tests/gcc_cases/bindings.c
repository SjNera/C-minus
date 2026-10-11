#include <stdio.h>
#include <stdbool.h>
int type(int class) { return class + 1; }
int main(void) {
    int x = 10;
    int True = 9;
    { int x = 20; printf("%d ", x); }
    printf("%d %d %d\n", x, type(4), True);
    int a;
    bool b;
    a = b = 9;
    printf("%d %d\n", a, b);
    return 0;
}
