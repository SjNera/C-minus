#include <stdio.h>
#include <stdbool.h>

void increment(int *number) {
    *number = *number + 1;
}

void toggle(bool *enabled) {
    *enabled = !*enabled;
}

int main(void) {
    int count = 5;
    bool ready = false;
    int *counter = &count;
    bool *flag = &ready;

    increment(counter);
    toggle(flag);
    printf("count=%d ready=%d\n", count, ready);
    return 0;
}
