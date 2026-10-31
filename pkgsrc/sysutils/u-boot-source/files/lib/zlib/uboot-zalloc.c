// SPDX-License-Identifier: GPL-2.0+
/* Freestanding allocation for the common zlib implementation. */
#include <malloc.h>
#include <u-boot/zlib.h>

void *gzalloc(void *opaque, unsigned int items, unsigned int size)
{
	if (items && size > (~0U - 15) / items)
		return NULL;
	return malloc((items * size + 15) & ~15U);
}

void gzfree(void *opaque, void *address)
{
	free(address);
}
