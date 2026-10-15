/* SPDX-License-Identifier: MIT */
#include <stdio.h>

extern unsigned int _mesa_glapi_get_dispatch_table_size(void);

int
main(void)
{
	unsigned int count;

	count = _mesa_glapi_get_dispatch_table_size();
	(void)printf("Mesa dispatch table entries: %u\n", count);
	return count == 0 ? 1 : 0;
}
