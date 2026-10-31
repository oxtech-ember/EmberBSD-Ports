#include <stddef.h>
#include <regex.h>

/* A source-level consumer keeps its allocator and algorithm-selection policy. */
#define xdl_malloc(n) consumer_malloc(n)
#define xdl_calloc(n, s) consumer_calloc(n, s)
#define xdl_realloc(p, n) consumer_realloc(p, n)
#define xdl_free(p) consumer_free(p)
#define XDF_DIFF_ALGORITHM_MASK (XDF_PATIENCE_DIFF | XDF_HISTOGRAM_DIFF)
#include "xdiff/xdiff.h"

_Static_assert(XDF_DIFF_ALG(XDF_PATIENCE_DIFF | XDF_NEED_MINIMAL) ==
    XDF_PATIENCE_DIFF, "consumer diff algorithm mask was overwritten");

int main(void) { return 0; }
