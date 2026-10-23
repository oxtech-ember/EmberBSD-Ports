/*
 * Check the real readline history parser with a moving allocation ledger.
 * Include the configured upstream readline.c through the compiler's -I path.
 * Link the remaining implementation from the same libedit static library.
 * Prepared with AI assistance. SPDX-License-Identifier: BSD-2-Clause
 */
#include <sys/types.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct ha_slot {
	void *ptr;
	size_t size;
	int live;
};
static struct ha_slot ha_slots[64];
static size_t ha_count, ha_live;
static int ha_bad_free, ha_realloc_calls, ha_fail_realloc, ha_fail_strdup;

static void *
ha_alloc(size_t size)
{
	void *ptr;

	if (ha_count == sizeof(ha_slots) / sizeof(ha_slots[0]))
		abort();
	ptr = malloc(size);
	if (ptr == NULL)
		abort();
	ha_slots[ha_count++] = (struct ha_slot){ ptr, size, 1 };
	ha_live++;
	return ptr;
}

static void
ha_free(void *ptr)
{
	size_t i;

	if (ptr == NULL)
		return;
	for (i = 0; i < ha_count; i++) {
		if (ha_slots[i].ptr == ptr && ha_slots[i].live) {
			ha_slots[i].live = 0;
			ha_live--;
			return;
		}
	}
	ha_bad_free++;
}

static void *
ha_realloc(void *ptr, size_t size)
{
	void *next;
	size_t i;

	if (++ha_realloc_calls == ha_fail_realloc) {
		errno = ENOMEM;
		return NULL;
	}
	next = ha_alloc(size);
	if (ptr != NULL) {
		for (i = 0; i < ha_count; i++) {
			if (ha_slots[i].ptr == ptr && ha_slots[i].live) {
				memcpy(next, ptr, size < ha_slots[i].size ?
				    size : ha_slots[i].size);
				break;
			}
		}
		if (i == ha_count)
			abort();
		ha_free(ptr);
	}
	return next;
}

static char *
ha_strdup(const char *text)
{
	char *copy;
	size_t size;

	if (ha_fail_strdup) {
		errno = ENOMEM;
		return NULL;
	}
	size = strlen(text) + 1;
	copy = ha_alloc(size);
	memcpy(copy, text, size);
	return copy;
}

/* Keep the entire production translation unit and its static helpers. */
#define realloc ha_realloc
#define free ha_free
#define strdup ha_strdup
#include "readline.c"
#undef realloc
#undef free
#undef strdup

static int
ha_case(const char *name, int to, const char *input, const char *search,
    int fail_realloc, int fail_strdup, int expected, const char *result,
    const char *remaining)
{
	const char *cursor = input;
	char *owned = ha_alloc(8);
	int status, bad;
	size_t i;

	memcpy(owned, "old", 4);
	ha_realloc_calls = 0;
	ha_fail_realloc = fail_realloc;
	ha_fail_strdup = fail_strdup;
	status = to ? getto(&cursor, &owned, "abc", '/') :
	    getfrom(&cursor, &owned, search, '/');
	bad = status != expected;
	if (result != NULL)
		bad |= owned == NULL || strcmp(owned, result) != 0;
	else
		bad |= owned != NULL;
	if (remaining != NULL)
		bad |= strcmp(cursor, remaining) != 0;
	if (fail_realloc != 0)
		bad |= ha_realloc_calls != fail_realloc;
	ha_free(owned);
	bad |= ha_live != 0 || ha_bad_free != 0;
	if (bad)
		fprintf(stderr, "%s: status=%d live=%zu invalid-free=%d realloc=%d\n",
		    name, status, ha_live, ha_bad_free, ha_realloc_calls);
	/* Delay physical frees so stale addresses cannot alias a later allocation. */
	for (i = 0; i < ha_count; i++)
		free(ha_slots[i].ptr);
	memset(ha_slots, 0, sizeof(ha_slots));
	ha_count = ha_live = 0;
	ha_bad_free = 0;
	return bad;
}

int
main(int argc, char **argv)
{
	int failed = 0, cases = 0;
	size_t i;
	const size_t lengths[] = { 15, 16, 17, 31, 32, 33, 64 };
	char input[80], expected[65];
	int ownership = argc == 1 || strcmp(argv[1], "ownership") == 0;
	int boundaries = argc == 1 || strcmp(argv[1], "boundaries") == 0;

	if (argc > 2 || (!ownership && !boundaries))
		return EXIT_FAILURE;
#define CASE(...) do { cases++; failed += ha_case(__VA_ARGS__); } while (0)
	if (ownership) {
		CASE("from-initial-failure", 0, "abc/value/", NULL, 1, 0, 0, NULL, NULL);
		CASE("from-moved-growth-failure", 0,
		    "abcdefghijklmnopqrstuvwxyz0123456789/value/", NULL, 2, 0, 0, NULL, NULL);
		CASE("from-search-dup-failure", 0, "/value/", "search", 0, 1, 0, NULL, NULL);
		CASE("from-empty-no-search", 0, "/value/", NULL, 0, 0, -1, NULL, NULL);
		CASE("from-search-no-delimiter", 0, "", "search", 0, 0, -1, NULL, "");
		CASE("from-search-no-replacement", 0, "/", "search", 0, 0, -1, NULL, "");
		CASE("from-search-success", 0, "/value/", "search", 0, 0, 1, "search", "value/");
		CASE("from-escaped-delimiter", 0, "a\\/b/value/", NULL, 0, 0, 1, "a/b", "value/");
		CASE("from-no-delimiter", 0, "abc", NULL, 0, 0, -1, NULL, "");
		CASE("from-no-replacement", 0, "abc/", NULL, 0, 0, -1, NULL, "");
		CASE("to-initial-failure", 1, "value/", NULL, 1, 0, -1, NULL, "value/");
		CASE("to-growth-failure", 1, "abcdefghijklmnopqrstuvwxyz/", NULL, 2, 0, -1, NULL, NULL);
		CASE("to-no-delimiter", 1, "value", NULL, 0, 0, -1, NULL, "");
		CASE("to-substitution", 1, "x&y/", NULL, 0, 0, 1, "xabcy", "/");
	}
	if (boundaries) {
		for (i = 0; i < sizeof(lengths) / sizeof(lengths[0]); i++) {
			memset(expected, 'a', lengths[i]);
			expected[lengths[i]] = '\0';
			(void)snprintf(input, sizeof(input), "%s/value/", expected);
			CASE("from-boundary", 0, input, NULL, 0, 0, 1, expected, "value/");
		}
	}
	if (failed != 0)
		return EXIT_FAILURE;
	printf("PASS: %d actual history parser allocation and boundary cases\n", cases);
	return EXIT_SUCCESS;
}
