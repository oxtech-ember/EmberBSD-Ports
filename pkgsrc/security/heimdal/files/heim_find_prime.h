/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#ifndef HEIM_FIND_PRIME_H
#define HEIM_FIND_PRIME_H
#include <tommath.h>
#ifndef HEIM_MP_ADD_D
#define HEIM_MP_ADD_D mp_add_d
#endif
#ifndef HEIM_MP_PRIME_IS_PRIME
#define HEIM_MP_PRIME_IS_PRIME mp_prime_is_prime
#endif
static int
heim_find_prime(mp_int *a, int rounds)
{
#ifdef MP_8BIT
    const int max_rounds = 31;
#else
    const int max_rounds = 256;
#endif
    mp_bool prime;
    if (rounds <= 0 || rounds > max_rounds || mp_isneg(a))
        return MP_VAL;
    if (mp_iseven(a) && HEIM_MP_ADD_D(a, 1, a) != MP_OKAY)
        return MP_VAL;
    for (;;) {
        if (HEIM_MP_PRIME_IS_PRIME(a, rounds, &prime) != MP_OKAY)
            return MP_VAL;
        if (prime == MP_YES)
            return MP_YES;
        if (HEIM_MP_ADD_D(a, 2, a) != MP_OKAY)
            return MP_VAL;
    }
}
#endif
