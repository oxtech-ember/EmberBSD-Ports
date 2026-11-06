#include <stdio.h>
#include <stdlib.h>
__attribute__((constructor)) static void loaded(void) { const char *p = getenv("EMBER_GSS_MARKER"); FILE *f = p ? fopen(p, "w") : NULL; if (f) { fputs("loaded\n", f); fclose(f); } }
