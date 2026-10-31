#include <stddef.h>
#include <regex.h>
#include "xdiff/xdiff.h"

_Static_assert(XDF_DIFF_ALG(XDF_PATIENCE_DIFF | XDF_NEED_MINIMAL) ==
    (XDF_PATIENCE_DIFF | XDF_NEED_MINIMAL), "Git's default algorithm mask changed");

int main(void) { return 0; }
