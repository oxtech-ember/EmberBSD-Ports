/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Ordinary byte-order conversion checks. */
#include "compat.h"

int
main(void)
{
	unsigned char data[8];
	const unsigned char expected[] = { 0x01, 0x23, 0x45, 0x67,
	                                  0x89, 0xab, 0xcd, 0xef };
	unsigned int i;

	be64enc(data, UINT64_C(0x0123456789abcdef));
	for (i = 0; i < sizeof(data); i++)
	    if (data[i] != expected[i])
	        return 1;
	if (be64dec(data) != UINT64_C(0x0123456789abcdef) ||
	    be32dec(data) != UINT32_C(0x01234567) ||
	    be16dec(data) != UINT16_C(0x0123))
	    return 1;
	be32enc(data, UINT32_C(0x89abcdef));
	return be32dec(data) != UINT32_C(0x89abcdef);
}
