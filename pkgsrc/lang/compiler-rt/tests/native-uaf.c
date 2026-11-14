#include <stdlib.h>
__attribute__((noinline)) static int read_after_free(volatile char *p) { return p[0]; }
int main(void) { char *p = malloc(8); if (!p) return 2; p[0] = 7; free(p); return read_after_free(p); }
