/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <config.h>
#include <stdint.h>
#include <obstack.h>

int
main(void)
{
	char buffer[128];
	unsigned int offset, shift;

	for (shift = 0; shift <= 4; shift++) {
		uintptr_t mask = ((uintptr_t)1 << shift) - 1;
		for (offset = 0; offset < 32; offset++) {
			char *p = buffer + offset;
			char *aligned = __PTR_ALIGN(buffer, p, mask);
			uintptr_t expected = ((uintptr_t)p + mask) & ~mask;

			if ((uintptr_t)aligned != expected)
				return 1;
		}
	}
	return 0;
}
