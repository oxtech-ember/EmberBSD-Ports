// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
#include <gbm.h>
extern "C" __attribute__((visibility("default"))) int gbm_bo_get_fd_for_plane(gbm_bo*, int plane) { return 37 + plane; }
