/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */

#include <stdlib.h>

/* The intentional leak is the runtime's LeakSanitizer positive control. */
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wanalyzer-malloc-leak"
#endif
static __attribute__((noinline)) void
leak_allocation(void)
{
	volatile unsigned char *allocation = malloc(37);

	if (allocation == NULL)
		exit(EXIT_FAILURE);

	/* Keep the allocation observable until this stack frame returns. */
	allocation[0] = 0xa5;
}
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif

int
main(void)
{
	leak_allocation();
	return EXIT_SUCCESS;
}
