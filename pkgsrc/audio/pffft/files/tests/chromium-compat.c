/* SPDX-License-Identifier: BSD-2-Clause */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <pffft/pffft.h>
#include <pffft/pffft_double.h>

#define TEST_PRECISION(T, PREFIX, SETUP, EPS) do {                            \
    int kind, ordered, scratch_mode;                                           \
    for (kind = 0; kind < 2; ++kind)                                          \
      for (ordered = 0; ordered < 2; ++ordered)                               \
        for (scratch_mode = (getenv("PFFFT_TEST_SUPPLIED_WORK") ? 1 : 0); scratch_mode < 2; ++scratch_mode) {            \
          const int n = 128, count = n * (kind ? 2 : 1);                     \
          T *input = PREFIX##_aligned_malloc(count * sizeof(T));              \
          T *freq = PREFIX##_aligned_malloc(count * sizeof(T));               \
          T *output = PREFIX##_aligned_malloc(count * sizeof(T));             \
          T *work = PREFIX##_aligned_malloc(count * sizeof(T));               \
          SETUP *setup = PREFIX##_new_setup(n, kind ? PFFFT_COMPLEX : PFFFT_REAL); \
          if (!input || !freq || !output || !work || !setup) return 2;        \
          for (int i = 0; i < count; ++i) input[i] = (T)(0.25 + sin(i * 0.3)); \
          if (ordered) {                                                      \
            PREFIX##_transform_ordered(setup,input,freq,scratch_mode ? work : NULL,PFFFT_FORWARD); \
            PREFIX##_transform_ordered(setup,freq,output,scratch_mode ? work : NULL,PFFFT_BACKWARD); \
          } else {                                                            \
            PREFIX##_transform(setup,input,freq,scratch_mode ? work : NULL,PFFFT_FORWARD); \
            PREFIX##_transform(setup,freq,output,scratch_mode ? work : NULL,PFFFT_BACKWARD); \
          }                                                                   \
          for (int i = 0; i < count; ++i)                                    \
            if (fabs((double)(output[i] / n - input[i])) > (EPS)) return 3;  \
          PREFIX##_destroy_setup(setup);                                      \
          PREFIX##_aligned_free(input); PREFIX##_aligned_free(freq);          \
          PREFIX##_aligned_free(output); PREFIX##_aligned_free(work);         \
        }                                                                     \
  } while (0)

#ifdef PFFFT_TEST_MSVC_ALLOC
extern int pffft_test_allocations, pffft_test_frees;
#endif
int main(void)
{
#ifndef PFFFT_SIMD_DISABLE
    validate_pffft_simd();
#endif
    TEST_PRECISION(float, pffft, PFFFT_Setup, 0.0001);
    TEST_PRECISION(double, pffftd, PFFFTD_Setup, 0.000000001);
#ifdef PFFFT_TEST_MSVC_ALLOC
    if (getenv("PFFFT_TEST_FAIL_ALLOC")) {
        if (pffft_test_allocations != 16 || pffft_test_frees != 0) return 4;
    } else if (pffft_test_allocations != 32 || pffft_test_frees != 32) return 4;
#endif
    puts("PFFFT compatibility roundtrips PASS");
    return 0;
}
