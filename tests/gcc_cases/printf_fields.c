#include <stdio.h>

int main(void) {
    int n = printf("[%+06d][% 5i][%-6.3d][%08.4d][%.0d][%5.0d]\n",
                   23, -7, 4, -9, 0, 0);
    printf("n=%d\n", n);
    printf("[%*.*d][%*s][%.*s][%3c][%-3c]\n", 8, 4, -12, -6, "hi", 4, "café", 65, 66);
    printf("[%0*d][%.*d][%+ .0d][%.s]\n", -5, 7, -1, 7, 0, "xyz");
    return 0;
}
