/* SPDX-License-Identifier: BSD-2-Clause */
/* EmberBSD contributors (AI-assisted). Test the prepared Mesa header. */
#include "u_dynarray.h"

static unsigned overlaps;

static void *
checked_copy(void *dest, const void *src, size_t size)
{
	if (dest == src)
		overlaps++;
	return memmove(dest, src, size);
}

#undef memcpy
#define memcpy checked_copy

int
main(void)
{
	int data[] = { 1, 2, 3, 4 };
	struct util_dynarray array = {
		.data = data, .size = sizeof(data), .capacity = sizeof(data)
	};

	util_dynarray_delete_unordered(&array, int, 4);
	if (array.size != 3 * sizeof(int) || overlaps != 0)
		return 1;
	util_dynarray_delete_unordered(&array, int, 1);
	if (array.size != 2 * sizeof(int) || data[0] != 3 || data[1] != 2 ||
	    overlaps != 0)
		return 2;
	util_dynarray_delete_unordered(&array, int, 9);
	if (array.size != 2 * sizeof(int) || data[0] != 3 || data[1] != 2 ||
	    overlaps != 0)
		return 3;
	util_dynarray_delete_unordered(&array, int, 2);
	if (array.size != sizeof(int) || data[0] != 3 || overlaps != 0)
		return 4;
	return 0;
}
