/* SPDX-License-Identifier: MIT */
/* Compiler input only. The GPU VA must be mapped before any GPU execution. */
#include "imagination/pco/usclib/libcl.h"

KERNEL(1)
cs_probe_store(void)
{
   /* The packet can pad this dispatch to 32 lanes. Only lane zero writes. */
   if (nir_load_instance_num_pco() != 0U)
      return;

   global uint *output = (global uint *)0x8000000000UL;
   *output = 0x13579bdfU;
}
