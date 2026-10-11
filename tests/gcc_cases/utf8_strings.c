#include <stdio.h>

int main(void) {
    int n = printf("Mabuhay: %s 世界\n", "café ñ");
    printf("bytes=%d\n", n);
    printf("[%8s][%-8.4s]\n", "é", "ééé");
    return 0;
}
