#include <limits.h>
int main(void) { volatile int x = INT_MAX; volatile int y = x + 1; return y == 0; }
