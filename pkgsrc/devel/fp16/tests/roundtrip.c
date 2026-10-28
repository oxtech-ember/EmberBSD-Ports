/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). */
#include <assert.h>
#include <stdint.h>
#include <fp16.h>
int main(void) {
  assert(fp16_ieee_from_fp32_value(1.0f) == UINT16_C(0x3c00));
  assert(fp16_ieee_from_fp32_value(-2.0f) == UINT16_C(0xc000));
  assert(fp16_ieee_to_fp32_value(UINT16_C(0x3c00)) == 1.0f);
  assert(fp16_ieee_to_fp32_value(UINT16_C(0xc000)) == -2.0f);
  return 0;
}
