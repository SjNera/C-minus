#include <stdio.h>
#include <stdbool.h>

void add(int *, int);
void swap(int *left, int *right);

void add(int *value, int amount) {
    if (amount) {
        *value = *value + 1;
        add(value, amount - 1);
    }
}

void swap(int *left, int *right) {
    int temporary = *left;
    *left = *right;
    *right = temporary;
}

void redirect(int *pointer, int *replacement) {
    pointer = replacement;
    *pointer = *pointer + 10;
}

int local_copy(int value) {
    int *pointer = &value;
    *pointer = 99;
    return value;
}

void toggle(bool *flag) {
    *flag = 42;
    *flag = !*flag;
}

int main(void) {
    int a = 2;
    int b = 7;
    int *pointer = &a;
    add(pointer, 3);
    swap(&a, &b);
    redirect(pointer, &b);
    printf("values %d %d %d\n", a, b, *pointer);
    int copied = local_copy(a);
    printf("copy %d %d\n", a, copied);
    bool flag = true;
    toggle(&flag);
    printf("bool %d\n", flag);
    swap(&a, &a);
    printf("alias %d\n", a);
    return 0;
}
