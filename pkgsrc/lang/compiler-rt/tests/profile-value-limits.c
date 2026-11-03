/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). */
#include <assert.h>
#include <stdint.h>
#include "InstrProfiling.h"
#include "InstrProfilingInternal.h"
int __llvm_profile_runtime = 0;
int main(void) {
  ValueProfNode b = { .Value = 22, .Count = UINT64_MAX, .Next = 0 };
  ValueProfNode a = { .Value = 11, .Count = UINT64_MAX, .Next = &b };
  ValueProfNode *slots[1] = { &a };
  __llvm_profile_data d = { 0 };
  d.Values = slots;
  lprofSetMaxValsPerSite(2);
  __llvm_profile_instrument_target_value(33, &d, 0, 1);
  assert(a.Value == 11 && a.Count == UINT64_MAX - 1 && b.Count == UINT64_MAX);
  a.Count = UINT64_MAX;
  __llvm_profile_instrument_target_value(33, &d, 0, UINT64_MAX);
  assert(a.Value == 33 && a.Count == UINT64_MAX && b.Value == 22 && b.Count == UINT64_MAX);
  lprofSetMaxValsPerSite(0);
  __llvm_profile_instrument_target_value(22, &d, 0, 1);
  __llvm_profile_instrument_target_value(44, &d, 0, 1);
  assert(a.Value == 33 && a.Count == UINT64_MAX && b.Value == 22 && b.Count == UINT64_MAX);
  d.Values = 0;
  __llvm_profile_instrument_target_value(55, &d, 0, 1);
  assert(d.Values == 0);
  return 0;
}
