/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */

#include <stdlib.h>

int
main(void)
{
	const void *allocation = malloc(37);

	if (allocation == NULL)
		return EXIT_FAILURE;

	/* Keep this allocation live. This is the LeakSanitizer positive control. */
	// cppcheck-suppress memleak
	return EXIT_SUCCESS;
}
