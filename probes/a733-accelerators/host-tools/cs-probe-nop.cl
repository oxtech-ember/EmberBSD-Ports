/*
 * Based on Mesa common.cl, Copyright 2025 Imagination Technologies Ltd.
 * SPDX-License-Identifier: MIT
 */
#include "compiler/libcl/libcl.h"

KERNEL(1)
cs_probe_nop(void)
{
   return;
}
