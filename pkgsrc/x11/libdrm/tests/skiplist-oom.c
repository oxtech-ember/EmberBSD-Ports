/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: AI-assisted EmberBSD; actual-source skip-list allocation regression. */

#include <stdio.h>
#include <stdlib.h>

#include "xf86drm.h"

static int alloc_calls;
static int successful_allocations;
static int free_calls;
static int fail_at = -1;
static int fail_random;
static int random_state;

void *drmMalloc(int);
void drmFree(void *);
void *drmRandomCreate(unsigned long);
unsigned long drmRandom(void *);

void *
drmMalloc(int size)
{
	int call;
	void *ptr;

	call = alloc_calls++;
	if (call == fail_at)
		return NULL;
	ptr = malloc((size_t)size);
	if (ptr != NULL)
		successful_allocations++;
	return ptr;
}

void
drmFree(void *ptr)
{
	if (ptr != NULL) {
		free_calls++;
		free(ptr);
	}
}

void *
drmRandomCreate(unsigned long seed)
{
	(void)seed;
	if (fail_random)
		return NULL;
	return &random_state;
}

unsigned long
drmRandom(void *state)
{
	(void)state;
	return 0;
}

#define CHECK(expression, message) do { \
	if (!(expression)) { \
		fprintf(stderr, "FAIL: %s\n", message); \
		return EXIT_FAILURE; \
	} \
} while (0)

int
main(void)
{
	void *list;
	int result;

	alloc_calls = 0;
	successful_allocations = 0;
	free_calls = 0;
	fail_at = 0;
	list = drmSLCreate();
	CHECK(list == NULL, "first allocation failure returns NULL");
	CHECK(alloc_calls == 1 && successful_allocations == 0 && free_calls == 0,
	    "first allocation failure has no leaked object");
	puts("PASS: list allocation failure");

	alloc_calls = 0;
	successful_allocations = 0;
	free_calls = 0;
	fail_at = 1;
	list = drmSLCreate();
	CHECK(list == NULL, "head allocation failure returns NULL");
	CHECK(alloc_calls == 2 && successful_allocations == 1 && free_calls == 1,
	    "head allocation failure frees the list object");
	puts("PASS: head allocation failure cleanup");

	alloc_calls = 0;
	successful_allocations = 0;
	free_calls = 0;
	fail_at = -1;
	list = drmSLCreate();
	CHECK(list != NULL, "list creation succeeds");
	CHECK(alloc_calls == 2 && successful_allocations == 2 && free_calls == 0,
	    "list creation allocation count");

	fail_random = 1;
	result = drmSLInsert(list, 100, NULL);
	CHECK(result == -1, "random-state allocation failure returns -1");
	CHECK(alloc_calls == 2 && successful_allocations == 2 && free_calls == 0,
	    "random-state failure allocates no node");
	puts("PASS: insertion random-state failure");

	fail_random = 0;
	fail_at = 2;
	result = drmSLInsert(list, 100, NULL);
	CHECK(result == -1, "node allocation failure returns -1");
	CHECK(alloc_calls == 3 && successful_allocations == 2 && free_calls == 0,
	    "node allocation failure leaves no allocated node");
	puts("PASS: insertion node allocation failure");

	fail_at = -1;
	result = drmSLInsert(list, 100, NULL);
	CHECK(result == 0, "retry after allocation failure inserts key");
	result = drmSLInsert(list, 100, NULL);
	CHECK(result == 1, "duplicate insertion retains return value 1");
	CHECK(alloc_calls == 4 && successful_allocations == 3,
	    "duplicate insertion does not allocate another node");
	CHECK(drmSLDestroy(list) == 0, "destroy succeeds");
	CHECK(free_calls == 3, "destroy frees list, head, and inserted node");
	puts("PASS: insertion recovery, duplicate semantics, and destruction");
	return EXIT_SUCCESS;
}
