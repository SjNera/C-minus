#include <stdio.h>

int main(void) {
    int number = 1;
    int *pointer = &number;
    int i = 0;
    for (; i < 6; *pointer = *pointer + 1) {
        i = i + 1;
        if (i == 2) continue;
        if (i == 4) break;
    }
    printf("for %d %d\n", number, i);
    while (*pointer < 6) {
        *pointer = *pointer + 1;
        if (*pointer == 5) continue;
    }
    do {
        *pointer = *pointer + 1;
        if (*pointer == 7) continue;
    } while (*pointer < 8);
    printf("loops %d\n", number);
    {
        int number = 30;
        int *inner = &number;
        *inner = 40;
        printf("shadow %d %d\n", number, *pointer);
    }
    for (int j = 0; j < 3; j = j + 1) {
        int temporary = j;
        int *alias = &temporary;
        *alias = *alias + 10;
        printf("%d ", temporary);
    }
    printf("\nouter %d\n", number);
    return 0;
}
