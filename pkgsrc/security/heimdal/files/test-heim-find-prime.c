/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <tommath.h>
#include <assert.h>
static int fail_add, fail_prime;
static mp_err test_add(const mp_int *a, mp_digit b, mp_int *c) {
    return fail_add ? MP_MEM : mp_add_d(a, b, c);
}
static mp_err test_prime(const mp_int *a, int t, mp_bool *b) {
    return fail_prime ? MP_MEM : mp_prime_is_prime(a, t, b);
}
#define HEIM_MP_ADD_D test_add
#define HEIM_MP_PRIME_IS_PRIME test_prime
#include "heim_find_prime.h"
int main(void) {
    mp_int a;
    assert(mp_init(&a) == MP_OKAY);
    mp_set(&a, 2); assert(heim_find_prime(&a, 1) == MP_YES && mp_cmp_d(&a, 3) == MP_EQ);
    mp_set(&a, 3); assert(heim_find_prime(&a, 1) == MP_YES && mp_cmp_d(&a, 3) == MP_EQ);
    mp_set(&a, 9); assert(heim_find_prime(&a, 1) == MP_YES && mp_cmp_d(&a, 11) == MP_EQ);
    assert(heim_find_prime(&a, 0) == MP_VAL);
#ifdef MP_8BIT
    assert(heim_find_prime(&a, 31) == MP_YES);
    assert(heim_find_prime(&a, 32) == MP_VAL);
#else
    assert(heim_find_prime(&a, 256) == MP_YES);
    assert(heim_find_prime(&a, 257) == MP_VAL);
#endif
    a.sign = MP_NEG; assert(heim_find_prime(&a, 1) == MP_VAL); a.sign = MP_ZPOS;
    mp_set(&a, 2); fail_add = 1; assert(heim_find_prime(&a, 1) == MP_VAL); fail_add = 0;
    mp_set(&a, 3); fail_prime = 1; assert(heim_find_prime(&a, 1) == MP_VAL);
    mp_clear(&a);
    return 0;
}
