/* SPDX-License-Identifier: MIT */
/* Compiler input only. The GPU VA must be mapped before any GPU execution. */
#include "compiler/libcl/libcl.h"

KERNEL(1)
cs_probe_store(void)
{
   global uint *output = (global uint *)0x8000000000UL;
   *output = 0x13579bdfU;
}
