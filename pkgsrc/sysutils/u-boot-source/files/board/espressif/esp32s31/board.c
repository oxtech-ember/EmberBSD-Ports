// SPDX-License-Identifier: GPL-2.0+
/*
 * ESP32-S31 board support.
 *
 * Copyright (C) 2026, Espressif Systems (Shanghai) CO LTD
 */

#include <init.h>
#include <env.h>
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

#if IS_ENABLED(CONFIG_ESP32S31_NOR_BOOT)
/* SPL records verified loadables in the firmware DT passed by OpenSBI. */
static bool s31_fit_payload_ready(const void *fdt, const char *path,
				 u32 address, u32 min_size, u32 max_size)
{
	const fdt32_t *load, *size;
	int node, len;
	u32 bytes;

	if (!fdt || fdt_check_header(fdt))
		return false;
	node = fdt_path_offset(fdt, path);
	if (node < 0)
		return false;
	load = fdt_getprop(fdt, node, "load", &len);
	if (!load || len != 2 * sizeof(*load) || fdt32_to_cpu(load[0]) ||
	    fdt32_to_cpu(load[1]) != address)
		return false;
	size = fdt_getprop(fdt, node, "size", &len);
	if (!size || len != sizeof(*size))
		return false;
	bytes = fdt32_to_cpu(*size);
	return bytes >= min_size && bytes <= max_size;
}
#endif

int board_late_init(void)
{
	puts("ESP32-S31 U-Boot active\n");

#if IS_ENABLED(CONFIG_ESP32S31_NOR_BOOT)
	/* A UART recovery FIT need not contain the persistent payloads. */
	if (s31_fit_payload_ready(gd->fdt_blob, "/fit-images/root",
				  0x50000000, 0x400000, 0x400000) &&
	    s31_fit_payload_ready(gd->fdt_blob, "/fit-images/kernel",
				  0x50c00000, 1, 0x370000))
		return env_set("bootcmd", "setenv initrd_high ffffffff; "
			       "setenv fdt_high 50500000; setenv bootargs -s; "
			       "setenv verify yes; bootm 50c00000 50000000:400000");
#endif
	return 0;
}
