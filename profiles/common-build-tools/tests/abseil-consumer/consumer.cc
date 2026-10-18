// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted); installed Abseil string and stacktrace API.
#include <cstdio>
#include <string>

#include "absl/debugging/stacktrace.h"
#include "absl/strings/str_cat.h"

ABSL_ATTRIBUTE_NOINLINE static int CaptureStack(void** frames, int capacity) {
  const int depth = absl::GetStackTrace(frames, capacity, 0);
  volatile int observed = depth;
  return observed;
}

ABSL_ATTRIBUTE_NOINLINE static int NestedStack(void** frames, int capacity) {
  const int depth = CaptureStack(frames, capacity);
  volatile int observed = depth;
  return observed;
}

int main() {

  const std::string actual = absl::StrCat("EmberBSD/", 36, ".", 2);
  if (actual != "EmberBSD/36.2") return 1;
  void* frames[16] = {};
  const int depth = NestedStack(frames, 16);
  if (depth < 1 || depth > 16) {
    std::fprintf(stderr, "Invalid stacktrace depth: %d\n", depth);
    return 2;
  }
  for (int i = 0; i < depth; ++i) {
    if (frames[i] == nullptr) return 3;
  }
  std::printf("PASS: %s; %d stack frames\n", actual.c_str(), depth);
  return 0;
}
