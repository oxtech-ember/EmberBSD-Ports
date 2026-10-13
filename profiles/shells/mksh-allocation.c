/*
 * Check the real mksh lalloc.o with controlled realloc results.
 * Compile with the same flags as lalloc.c. Link with
 * -Wl,--wrap=realloc -Wl,--wrap=free.
 * Origin: EmberBSD, AI-assisted. SPDX-License-Identifier: ISC
 */

#include "sh.h"

#include <setjmp.h>

#ifdef MKSH_ALLOC_CATCH_UNDERRUNS
#error This regression requires the normal realloc allocator.
#endif

struct allocation {
	void *ptr;
	size_t size;
};

static struct allocation blocks[8];
static jmp_buf error_target;
static int expect_error;
static int fail_next;
static int move_next;
static unsigned int realloc_calls;
static const char *case_name;

void *__real_realloc(void *, size_t);
void __real_free(void *);
void *__wrap_realloc(void *, size_t);
void __wrap_free(void *);

static void
require(int condition, const char *message)
{
	if (!condition) {
		fprintf(stderr, "%s: %s\n", case_name, message);
		exit(1);
	}
}

static size_t
block_index(void *ptr)
{
	size_t i;

	for (i = 0; i < sizeof(blocks) / sizeof(blocks[0]); i++)
		if (blocks[i].ptr == ptr)
			return (i);
	require(0, "unknown allocation");
	return (0);
}

void *
__wrap_realloc(void *ptr, size_t size)
{
	void *result;
	size_t i;

	i = block_index(ptr);
	realloc_calls++;
	if (fail_next) {
		fail_next = 0;
		errno = ENOMEM;
		return (NULL);
	}
	if (move_next && ptr != NULL) {
		move_next = 0;
		/* Allocate before freeing so the address must change. */
		result = malloc(size);
		require(result != NULL, "test allocation failed");
		memcpy(result, ptr, size < blocks[i].size ? size : blocks[i].size);
		__real_free(ptr);
	} else {
		result = __real_realloc(ptr, size);
		require(result != NULL, "unexpected allocation failure");
	}
	blocks[i].ptr = result;
	blocks[i].size = size;
	return (result);
}

void
__wrap_free(void *ptr)
{
	size_t i;

	if (ptr != NULL) {
		i = block_index(ptr);
		blocks[i].ptr = NULL;
		blocks[i].size = 0;
	}
	__real_free(ptr);
}

void
internal_errorf(const char *format, ...)
{
	(void)format;
	require(expect_error, "unexpected allocator error");
	longjmp(error_target, 1);
}

static unsigned int
live_blocks(void)
{
	size_t i;
	unsigned int count = 0;

	for (i = 0; i < sizeof(blocks) / sizeof(blocks[0]); i++)
		if (blocks[i].ptr != NULL)
			count++;
	return (count);
}

static int
is_in_area(Area *area, void *ptr)
{
	struct lalloc_common *item;
	unsigned int count = 0;

	for (item = area->next; item != NULL; item = item->next) {
		require(++count <= 3, "cyclic or oversized Area list");
		if ((char *)item + sizeof(ALLOC_ITEM) == ptr)
			return (1);
	}
	return (0);
}

static void
check_contents(char **items)
{
	size_t i, j;

	for (i = 0; i < 3; i++)
		for (j = 0; j < 32; j++)
			require(items[i][j] == (char)('a' + i), "old data changed");
}

static int
run_case(const char *operation, int position)
{
	/* Static objects retain defined values across the error longjmp. */
	static Area area;
	static char *items[3];
	static struct lalloc_common *old_head;
	static unsigned int old_calls;
	size_t i;
	int lost = 0;
	int empty = strcmp(operation, "new-fail") == 0 ||
	    strcmp(operation, "new-overflow") == 0;
	int overflow = strstr(operation, "overflow") != NULL;
	int multiply = strcmp(operation, "multiply-overflow") == 0;
	int move = strcmp(operation, "move") == 0;

	ainit(&area);
	memset(items, 0, sizeof(items));
	if (!empty)
		for (i = 0; i < 3; i++) {
			items[i] = aresize(NULL, 32, &area);
			memset(items[i], (int)('a' + i), 32);
		}
	old_head = area.next;
	old_calls = realloc_calls;
	expect_error = !move;
	if (setjmp(error_target) == 0) {
		if (move)
			move_next = 1;
		else if (!overflow)
			fail_next = 1;
		if (multiply)
			items[position] = aresize2(items[position], (size_t)-1,
			    2, &area);
		else
			items[position] = aresize(items[position],
			    overflow ? (size_t)-1 : 96, &area);
		require(move, "allocator error did not unwind");
	} else {
		require(expect_error, "resize unexpectedly failed");
	}
	expect_error = 0;
	require(!fail_next && !move_next, "injected realloc result not used");
	require(realloc_calls == old_calls + (overflow ? 0 : 1),
	    "wrong realloc call count");
	if (!move && area.next != old_head)
		lost = 1;
	if (!empty) {
		check_contents(items);
		for (i = 0; i < 3; i++)
			if (!is_in_area(&area, items[i]))
				lost = 1;
		if (move)
			require((char *)area.next + sizeof(ALLOC_ITEM) ==
			    items[position], "resized item is not the Area head");
	}
	afreeall(&area);
	require(area.next == NULL, "Area cleanup left a list");
	if (live_blocks() != 0)
		lost = 1;
	/* Drop test bookkeeping; an orphan must remain visible to Memcheck. */
	memset(blocks, 0, sizeof(blocks));
	memset(items, 0, sizeof(items));
	old_head = NULL;
	if (lost)
		fprintf(stderr, "%s: resize orphaned the caller's allocation\n",
		    case_name);
	else
		printf("PASS %s\n", case_name);
	return (lost);
}

int
main(void)
{
	static const char *operations[] = {
		"overflow", "fail", "move", "multiply-overflow"
	};
	static const char *positions[] = { "tail", "middle", "head" };
	char name[64];
	size_t i, j;
	int failures = 0;

	case_name = "new-fail";
	failures += run_case(case_name, 0);
	case_name = "new-overflow";
	failures += run_case(case_name, 0);
	for (i = 0; i < sizeof(operations) / sizeof(operations[0]); i++)
		for (j = 0; j < 3; j++) {
			snprintf(name, sizeof(name), "%s-%s", operations[i],
			    positions[j]);
			case_name = name;
			failures += run_case(operations[i], (int)j);
		}
	return (failures != 0);
}
