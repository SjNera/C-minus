#include <stdio.h>
#include <stdbool.h>

int result = (-7 / 3) * 3 + (-7 % 3);
int comparisons = (5 < 6) + (5 <= 5) + (9 > 8) + (9 >= 9) + (7 == 7) + (7 != 8);
int negation = -(-5) + !1;
int lazy_and = 0 && (1 / 0);
int lazy_or = 1 || (1 / 0);
bool condition = !0 && 4 >= 3 || false;
bool normalized = -12;

int main(void) {
    printf("%d %d %d %d %d %d %d\n", result, comparisons, negation,
           lazy_and, lazy_or, condition, normalized);
    return 0;
}
