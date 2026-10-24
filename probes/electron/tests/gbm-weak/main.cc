// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
#include <gbm.h>
#include "gbm-weak-declaration.h"
int main(int argc, char**) {
  if (argc == 1) return gbm_bo_get_fd_for_plane ? 1 : 0;
  if (!gbm_bo_get_fd_for_plane) return 2;
  return gbm_bo_get_fd_for_plane(nullptr, 5) == 42 ? 0 : 4;
}
