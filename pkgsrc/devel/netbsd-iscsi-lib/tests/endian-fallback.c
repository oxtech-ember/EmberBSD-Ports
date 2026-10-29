/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Ordinary conversion without endian macros. */
#include <sys/types.h>
#undef _BYTE_ORDER
#undef _BIG_ENDIAN
#include "compat.h"

int
main(void)
{
	uint64_t converted = ISCSI_HTOBE64(UINT64_C(0x0123456789abcdef));
	const uint8_t *bytes = (const uint8_t *)&converted;
	const uint8_t expected[] = { 0x01, 0x23, 0x45, 0x67,
	    0x89, 0xab, 0xcd, 0xef };
	unsigned int i;

	for (i = 0; i < sizeof(expected); i++)
		if (bytes[i] != expected[i])
			return 1;
	return 0;
}
