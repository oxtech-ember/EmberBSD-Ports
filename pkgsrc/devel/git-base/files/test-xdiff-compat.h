#ifndef TEST_XDIFF_COMPAT_H
#define TEST_XDIFF_COMPAT_H
#include <assert.h>
#include <ctype.h>
#include <limits.h>
#include <regex.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void *test_alloc(size_t);
void *test_calloc(size_t, size_t);
void *test_realloc(void *, size_t);
void test_free(void *);

#define xdl_malloc(n) test_alloc(n)
#define xdl_calloc(n, s) test_calloc(n, s)
#define xdl_realloc(p, n) test_realloc(p, n)
#define xdl_free(p) test_free(p)
#define XDF_DIFF_ALGORITHM_MASK (XDF_PATIENCE_DIFF | XDF_HISTOGRAM_DIFF)
#define UNUSED __attribute__((unused))
#define BUG(...) abort()
/* xemit calls this only with nonnegative context lengths. */
#define signed_add_overflows(a, b) ((a) > LONG_MAX - (b))

static inline int
regexec_buf(const regex_t *rx, const char *buf, size_t len, size_t n,
    regmatch_t *matches, int flags)
{
	(void)rx; (void)buf; (void)len; (void)n; (void)matches; (void)flags;
	abort(); /* This test does not supply ignore_regex. */
}
#endif
