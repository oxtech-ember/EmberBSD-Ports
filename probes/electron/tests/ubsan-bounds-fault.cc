// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// A sanitizer trap must reject this dynamic one-past array read.
int main(int argc, char**) {
  volatile int index = argc;
  int values[1] = {7};
  volatile int observed = values[index];
  (void)observed;
  return 0;
}
