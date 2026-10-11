#include <stdio.h>
#include <stdbool.h>

int total;
bool ready;
int *counter = &total;
bool *flag = &ready;
int *empty;

void update(void) {
    *counter = *counter + 5;
    *flag = true;
}

int main(void) {
    printf("start %d %d %d\n", total, ready, empty == 0);
    update();
    total = total + 1;
    int local = 20;
    empty = &local;
    *empty = *empty + 2;
    printf("end %d %d %d %d\n", total, ready, local, counter == &total);
    empty = 0;
    return 0;
}
