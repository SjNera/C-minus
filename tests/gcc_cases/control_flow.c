#include <stdio.h>
#include <stdbool.h>
int main(void) {
    int sum = 0;
    int i = 99;
    for (int i = 0; i < 4; i = i + 1) { sum = sum + i; }
    int count = 0;
    while (count < 2) { sum = sum + 10; count = count + 1; }
    do { sum = sum + 1; } while (false);
    int j = 0;
    do { j = j + 1; } while (j < 3);
    if (sum == 27 && j == 3) { for (; j < 5; j = j + 1) sum = sum + 2; }
    else if (sum < 0) sum = 0;
    else sum = -1;
    printf("%d %d %d\n", sum, i, j);
    return 0;
}
