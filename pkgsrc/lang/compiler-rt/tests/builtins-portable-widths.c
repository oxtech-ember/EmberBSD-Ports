/* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception */
/* Origin: EmberBSD (AI-assisted). Arithmetic checks of actual compiler-rt symbols. */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#if !defined(__SIZEOF_INT128__)
#error "this regression requires native 128-bit integer support"
#endif
extern int32_t __divmodsi4(int32_t, int32_t, int32_t *);
extern uint32_t __udivsi3(uint32_t, uint32_t);
extern uint32_t __umodsi3(uint32_t, uint32_t);
extern uint64_t __udivdi3(uint64_t, uint64_t);
extern uint64_t __umoddi3(uint64_t, uint64_t);
extern float __floattisf(__int128);
extern double __floatuntidf(unsigned __int128);
extern float __floatuntisf(unsigned __int128);

int main(void) {
    static const int32_t signed_values[] = { INT32_MIN, INT32_MIN + 1, -123456789, -7, -1, 0, 1, 7, 123456789, INT32_MAX };
    for (unsigned i = 0; i < sizeof(signed_values)/sizeof(signed_values[0]); i++) {
        for (unsigned j = 0; j < sizeof(signed_values)/sizeof(signed_values[0]); j++) {
            int32_t a = signed_values[i], b = signed_values[j], rem;
            if (!b || (a == INT32_MIN && b == -1)) continue;
            assert(__divmodsi4(a,b,&rem) == a/b && rem == a%b);
        }
    }
    static const uint64_t values[] = { 0, 1, 2, 3, UINT64_C(1) << 31,
        UINT64_C(1) << 32, UINT64_C(1) << 63, UINT64_MAX };
    for (unsigned i = 0; i < sizeof(values)/sizeof(values[0]); i++) {
        for (unsigned j = 1; j < sizeof(values)/sizeof(values[0]); j++) {
            uint64_t a = values[i], b = values[j];
            assert(__udivdi3(a,b) == a/b && __umoddi3(a,b) == a%b);
            uint32_t a32 = (uint32_t)a, b32 = (uint32_t)b;
            if (b32)
                assert(__udivsi3(a32,b32) == a32/b32 &&
                    __umodsi3(a32,b32) == a32%b32);
        }
    }
    static const uint32_t values32[] = { 0, 1, 2, 3, UINT32_C(1) << 31, UINT32_MAX };
    for (unsigned i = 0; i < sizeof(values32)/sizeof(values32[0]); i++)
        for (unsigned j = 1; j < sizeof(values32)/sizeof(values32[0]); j++) {
            uint32_t a = values32[i], b = values32[j];
            assert(__udivsi3(a,b) == a/b && __umodsi3(a,b) == a%b);
        }
    uint64_t x = UINT64_C(0x369dea0f31a53f85);
    for (unsigned i = 0; i < 20000; i++) {
        x = x * UINT64_C(6364136223846793005) + 1;
        uint64_t a = x;
        x = x * UINT64_C(6364136223846793005) + 1;
        uint64_t b = x | 1;
        uint32_t a32 = (uint32_t)a, b32 = (uint32_t)b;
        assert(__udivsi3(a32,b32) == a32/b32 && __umodsi3(a32,b32) == a32%b32);
        assert(__udivdi3(a,b) == a/b && __umoddi3(a,b) == a%b);
    }
    assert(__floattisf(((__int128)1 << 100) + 1) == 0x1p100f);
    assert(__floattisf(-((__int128)1 << 100)) == -0x1p100f);
    assert(__floatuntidf(((unsigned __int128)1 << 100) + 1) == 0x1p100);
    assert(__floatuntidf(~(unsigned __int128)0) == 0x1p128);
    const unsigned __int128 base = (unsigned __int128)1 << 100;
    const unsigned __int128 unit = (unsigned __int128)1 << 77;
    assert(__floatuntisf(base + unit / 2) == 0x1p100f);
    assert(__floatuntisf(base + unit + unit / 2) == 0x1.000004p100f);
    assert(__builtin_isinf(__floatuntisf(~(unsigned __int128)0)));
    puts("PASS: signed boundaries, 20000 unsigned divisions and 128-bit conversion rounding");
    return 0;
}
