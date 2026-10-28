#include <stdlib.h>
int run(void) {
  int *p = malloc(sizeof(*p));
  if (!p) return 0;
  *p = 42;
  int result = *p;
  free(p);
  return result;
}
