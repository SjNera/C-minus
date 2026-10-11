#include <stdio.h>
#include <stdbool.h>

int counter;
bool ready;
int quotient = -7 / 3;
int mod_result = 7 % -3;

void add(int amount) {
    counter = counter + amount;
    ready = counter > 0;
}

int echo(int counter) {
    counter = counter + 1;
    return counter;
}

void loop_globals(void) {
    for (counter = 0; counter < 4; counter = counter + 1) {
        if (counter == 1) continue;
        if (counter == 3) break;
    }
}

int bump(void) { return counter = counter + 1; }

int main(void) {
    printf("start %d %d %d %d\n", counter, ready, quotient, mod_result);
    add(5);
    printf("state %d %d %d\n", counter, ready, echo(10));
    { int counter = 99; printf("shadow %d\n", counter); }
    loop_globals();
    int last = bump();
    printf("end %d %d %d\n", counter, last, ready);
    return 0;
}
