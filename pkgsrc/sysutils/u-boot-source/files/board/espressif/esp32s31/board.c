// SPDX-License-Identifier: GPL-2.0+
/*
 * ESP32-S31 board support.
 *
 * Copyright (C) 2026, Espressif Systems (Shanghai) CO LTD
 */

#include <init.h>
#include <hang.h>
#include <errno.h>
#include <stdio.h>
#include <linux/libfdt.h>
#include <asm/global_data.h>

#include "psram-layout.h"

DECLARE_GLOBAL_DATA_PTR;

int board_fdt_blob_setup(void **fdtp)
{
	void *fdt = (void *)(uintptr_t)gd->arch.firmware_fdt_addr;

	if (!fdt || fdt_check_header(fdt) != 0)
		return -ENXIO;
	*fdtp = fdt;
	return 0;
}

/* Keep the relocation in the high part of the first 16 MiB of PSRAM. */
phys_addr_t board_get_usable_ram_top(phys_size_t total_size)
{
	const fdt32_t *reg;
	int node, len;

	if (!gd->fdt_blob || fdt_check_header(gd->fdt_blob))
		goto invalid;
	node = fdt_path_offset(gd->fdt_blob, "/memory@50000000");
	if (node < 0)
		goto invalid;
	reg = fdt_getprop(gd->fdt_blob, node, "reg", &len);
	if (!reg || len != 2 * sizeof(*reg) ||
	    fdt32_to_cpu(reg[0]) != S31_PSRAM_BASE ||
	    !s31_psram_size_supported(fdt32_to_cpu(reg[1])) ||
	    total_size > S31_PSRAM_RELOC_TOP - S31_PSRAM_RUNTIME_FLOOR)
		goto invalid;
	return S31_PSRAM_RELOC_TOP;
invalid:
	puts("Invalid firmware PSRAM bank for U-Boot relocation\n");
	hang();
}

/* Leave a bounded stack margin above the boot payload staging area. */
int arch_reserve_stacks(void)
{
	if (gd->start_addr_sp < S31_PSRAM_RUNTIME_FLOOR +
	    S31_PSRAM_STACK_MARGIN || gd->start_addr_sp > S31_PSRAM_RELOC_TOP)
		return -ENOMEM;
	return 0;
}

int board_init(void)
{
	return 0;
}

int board_late_init(void)
{
	puts("ESP32-S31 U-Boot active\n");

	return 0;
}
