#include <stdlib.h>
int main(void) { volatile int x = 42; char *p = malloc(4); if (!p) return 2; p[0] = 1; free(p); return x != 42; }
