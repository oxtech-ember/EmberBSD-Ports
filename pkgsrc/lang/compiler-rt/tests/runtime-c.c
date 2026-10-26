/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted).
 * Link and target-execution smoke for the selected compiler builtins.
 */
#include <stdio.h>

static volatile __int128 dividend = ((__int128)1 << 100) + 23;
static volatile __int128 divisor = 7;

int
main(void)
{
	__int128 quotient = dividend / divisor;
	__int128 remainder = dividend % divisor;

	if (quotient * divisor + remainder != dividend)
		return 1;
	puts("PASS: compiler-rt integer division");
	return 0;
}
