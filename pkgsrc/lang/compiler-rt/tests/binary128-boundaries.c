/* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception */
/* Origin: EmberBSD (AI-assisted). Target binary128 builtin boundaries. */
#define QUAD_PRECISION
#include "fp_lib.h"
#include <stdint.h>
#include <stdio.h>
#include <limits.h>
#if !defined(CRT_HAS_IEEE_TF) || !defined(__SIZEOF_FLOAT128__)
#error "requires the target IEEE binary128 type"
#endif
extern fp_t __multf3(fp_t, fp_t);
extern fp_t __divtf3(fp_t, fp_t);
extern fp_t __powitf2(fp_t, int);
static rep_t bits(uint64_t hi, uint64_t lo) { return ((rep_t)hi << 64) | lo; }
static int check(const char *name, fp_t actual, rep_t expected) {
    rep_t got = toRep(actual);
    if (got == expected) return 0;
    printf("FAIL %s: got %016llx%016llx expected %016llx%016llx\n", name,
        (unsigned long long)(got >> 64), (unsigned long long)got,
        (unsigned long long)(expected >> 64), (unsigned long long)expected);
    return 1;
}
int main(void) {
    int fail = 0;
    volatile fp_t one = fromRep(bits(UINT64_C(0x3fff000000000000),0));
    volatile fp_t two = fromRep(bits(UINT64_C(0x4000000000000000),0));
    volatile fp_t half = fromRep(bits(UINT64_C(0x3ffe000000000000),0));
    volatile fp_t zero = fromRep(0), inf = fromRep(infRep);
    volatile fp_t negone = fromRep(signBit | toRep(one));
    volatile fp_t max = fromRep(infRep - 1), minnormal = fromRep(implicitBit);
    volatile fp_t tiny = fromRep(1), three = fromRep(3);
    volatile fp_t carrya = fromRep(bits(UINT64_C(0x3fffffffffffffff), UINT64_MAX));
    volatile fp_t carryb = fromRep(toRep(one) + 1);
    volatile fp_t nan = fromRep(infRep | (implicitBit >> 1));
#define CHECK(n, actual, expected) (fail += check(n, actual, expected))
    CHECK("mul identity", __multf3(one, one), toRep(one));
    CHECK("mul sign", __multf3(negone, one), toRep(negone));
    CHECK("mul zero", __multf3(negone, zero), signBit);
    CHECK("mul inf", __multf3(inf, two), infRep);
    if (!crt_isnan(__multf3(nan, one))) { puts("FAIL mul nan"); fail++; }
    CHECK("mul overflow", __multf3(max, two), infRep);
    CHECK("mul normal to subnormal", __multf3(minnormal, half), implicitBit >> 1);
    CHECK("mul subnormal tie even zero", __multf3(tiny, half), 0);
    CHECK("mul subnormal tie even two", __multf3(three, half), 2);
    CHECK("mul rounding carry", __multf3(carrya, carryb), toRep(two));
    CHECK("div identity", __divtf3(one, one), toRep(one));
    CHECK("div sign", __divtf3(negone, two), signBit | toRep(half));
    CHECK("div subnormal", __divtf3(minnormal, two), implicitBit >> 1);
    CHECK("pow zero", __powitf2(two, 0), toRep(one));
    CHECK("pow negative exponent", __powitf2(two, -1), toRep(half));
    CHECK("pow sign", __powitf2(negone, 3), toRep(negone));
    CHECK("logb normal", __compiler_rt_logbX(two), toRep(one));
    CHECK("logb minimum normal", __compiler_rt_logbX(minnormal), toRep((fp_t)-16382));
    CHECK("logb minimum subnormal", __compiler_rt_logbX(tiny), toRep((fp_t)-16494));
    CHECK("logb zero", __compiler_rt_logbX(zero), signBit | infRep);
    CHECK("scalbn subnormal", __compiler_rt_scalbnX(tiny, 112), implicitBit);
    CHECK("scalbn normal to subnormal", __compiler_rt_scalbnX(minnormal, -1), implicitBit >> 1);
    CHECK("scalbn underflow", __compiler_rt_scalbnX(tiny, INT_MIN), 0);
    CHECK("scalbn overflow", __compiler_rt_scalbnX(max, INT_MAX), infRep);
    if (rep_clz((rep_t)1) != 127 || rep_clz(implicitBit) != 15) {
        puts("FAIL rep_clz"); fail++;
    }
    if (!fail) puts("PASS: binary128 builtins and fp_lib boundaries");
    return fail ? 1 : 0;
}
