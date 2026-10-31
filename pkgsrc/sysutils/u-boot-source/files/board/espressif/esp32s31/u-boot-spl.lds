/* SPDX-License-Identifier: GPL-2.0+ */
#include <generated/generic-asm-offsets.h>
#if !CONFIG_IS_ENABLED(SMP) || !CONFIG_IS_ENABLED(SYS_MALLOC_F) || \
    CONFIG_IS_ENABLED(HAVE_INIT_STACK) || \
    !defined(CONFIG_HAS_CUSTOM_SYS_INIT_SP_ADDR) || defined(CFG_MALLOC_F_ADDR)
#error "Recalculate the S31 SPL initial SRAM reservations"
#endif
#include "../../../arch/riscv/cpu/u-boot-spl.lds"
ASSERT(__bss_end <= (((CONFIG_CUSTOM_SYS_INIT_SP_ADDR & ~15) -
       (CONFIG_NR_CPUS << CONFIG_STACK_SIZE_SHIFT) -
       CONFIG_SPL_SYS_MALLOC_F_LEN - GENERATED_GBL_DATA_SIZE) & ~15),
       "S31 SPL BSS overlaps initial GD, malloc or CPU stacks");
ASSERT((CONFIG_CUSTOM_SYS_INIT_SP_ADDR & ~15) <= 0x2f07afb0,
       "S31 SPL stack overlaps ROM-reserved SRAM");
