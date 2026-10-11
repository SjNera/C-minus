#include <stdio.h>
int main(void) {
    printf("%c%s", 255, "hi\0ignored");
    printf("end\0ignored");
    return 0;
}
