#include <stdio.h>

int initialize(int *value) {
    *value = 7;
    return *value + 2;
}

int main(void) {
    int value = initialize(&value);
    int other;
    int *pointer = &other;
    *pointer = 15;
    int self_assigned = 4;
    int *self = &self_assigned;
    printf("%d %d %d\n", value, other, *self);
    return 0;
}
