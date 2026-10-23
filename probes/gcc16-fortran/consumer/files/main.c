/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; C entry point for actual Fortran runtime calls. */
#include <stdio.h>

extern void ember_fortran_c(double *);
extern void ember_fortran_f77_(int *);

int
main(void)
{
	double value = 0;
	int integer = 0;

	ember_fortran_c(&value);
	ember_fortran_f77_(&integer);
	if (value != 12.0 || integer != 42)
		return 1;
	puts("Fortran FC/F77 runtime: PASS");
	return 0;
}
