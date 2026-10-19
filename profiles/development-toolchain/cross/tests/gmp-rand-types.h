/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; check the GMP API type before variadic promotion. */
#ifndef EMBER_GMP_RAND_TYPES_H
#define EMBER_GMP_RAND_TYPES_H

#include <stdio.h>
#include "gmp.h"

/* Do not convert the argument: reject an incorrect type at its call site. */
#define EMBER_GMP_RAND_SIZE(value) \
	((void)sizeof(struct { \
	    _Static_assert(_Generic((value), unsigned long: 1, default: 0), \
	        "GMP random size must be unsigned long"); \
	    int unused; \
	}), (value))
#undef gmp_randinit
#define gmp_randinit(state, algorithm, size) \
	__gmp_randinit((state), (algorithm), EMBER_GMP_RAND_SIZE(size))

#endif
