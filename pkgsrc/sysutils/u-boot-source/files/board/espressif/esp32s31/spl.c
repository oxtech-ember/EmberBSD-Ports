// SPDX-License-Identifier: GPL-2.0+
/*
 * ESP32-S31 U-Boot SPL: the mask ROM's second-stage. Does first-stage SoC
 * bring-up (WDT, cache/MMU, PSRAM and clock tree), then receives a FIT
 * containing OpenSBI, U-Boot proper and a control DTB over UART.
 *
 * Copyright (C) 2026, Espressif Systems (Shanghai) CO LTD
 */

#include <spl.h>
#include <hang.h>
#include <stdio.h>
#include <asm/io.h>
#include <linux/libfdt.h>
#include <asm/sections.h>
#include <linux/bitops.h>

#include "spl_cache_mmu.h"
#include "spl_clk.h"
#include "spl_psram.h"
#include "psram-layout.h"

/* ROM-armed watchdogs (RTC WDT + super-WDT + MWDT0). Disabled from
 * harts_early_init (start.S, earliest C hook) so the chip doesn't reset a
 * few seconds into SPL.
 */
#define S31_RTC_WDT_BASE 0x20801000
#define S31_TIMG0_BASE   0x20580000
#define S31_WDT_WKEY     0x50D83AA1

#define S31_RTC_WDT_SWD_WPROTECT 0x20
#define S31_RTC_WDT_SWD_CONF     0x1C
#define S31_RTC_WDT_WPROTECT     0x18
#define S31_RTC_WDT_CONFIG0      0x00
#define S31_RTC_WDT_SWD_AUTO_FEED_EN BIT(18)

#define S31_TIMG0_WDT_WPROTECT   0x64
#define S31_TIMG0_WDT_CONFIG0    0x48

void harts_early_init(void)
{
	char *rtc = (char *)S31_RTC_WDT_BASE;
	char *tg0 = (char *)S31_TIMG0_BASE;

	/* super-WDT: auto-feed */
	writel(S31_WDT_WKEY, rtc + S31_RTC_WDT_SWD_WPROTECT);
	writel(readl(rtc + S31_RTC_WDT_SWD_CONF) | S31_RTC_WDT_SWD_AUTO_FEED_EN,
	       rtc + S31_RTC_WDT_SWD_CONF);
	writel(0, rtc + S31_RTC_WDT_SWD_WPROTECT);
	/* RTC WDT: unlock, clear config, re-lock */
	writel(S31_WDT_WKEY, rtc + S31_RTC_WDT_WPROTECT);
	writel(0, rtc + S31_RTC_WDT_CONFIG0);
	writel(0, rtc + S31_RTC_WDT_WPROTECT);
	/* MWDT0 (TIMG0) */
	writel(S31_WDT_WKEY, tg0 + S31_TIMG0_WDT_WPROTECT);
	writel(0, tg0 + S31_TIMG0_WDT_CONFIG0);
	writel(0, tg0 + S31_TIMG0_WDT_WPROTECT);
}

void spl_board_init(void)
{
	puts("ESP32-S31 SPL active\n");

	/* RAM-only trial: initialise PSRAM before receiving a FIT over UART. */
	puts("spl: cache/mmu begin\n");
	s31_spl_cache_mmu_init();
	puts("spl: cache/mmu done\n");
	puts("spl: PSRAM PMA begin\n");
	s31_spl_pma_psram_rwx();
	puts("spl: PSRAM PMA done\n");
	puts("spl: PSRAM init begin\n");
	if (psram_init()) {
		puts("spl: psram_init failed\n");
		hang();
	}
	if (!s31_psram_size_supported(psram_size_bytes())) {
		puts("spl: PSRAM capacity is too small for this boot map\n");
		hang();
	}

	/* Clock-tree bring-up. Order: MPLL (EMAC ref path; psram_init already
	 * did the PSRAM MPLL) -> CPU 40->320 MHz CPLL -> systimer peripheral
	 * clock for Linux's clocksource.
	 */
	s31_spl_mpll_enable();
	s31_spl_cpu_switch_to_cpll();
	s31_spl_systimer_clk_init();
	puts("ESP32-S31 PSRAM ready; waiting for UART FIT\n");
}

u32 spl_boot_device(void)
{
	return BOOT_DEVICE_UART;
}

/* SPL's control dtb is appended to the SPL image at _end. */
int board_fdt_blob_setup(void **fdtp)
{
	*fdtp = (void *)_end;
	return 0;
}

/* The firmware FDT is verified before this board-specific hardware fixup. */
void spl_perform_board_fixups(struct spl_image_info *spl_image)
{
	void *fdt = spl_image->fdt_addr;
	const fdt32_t *old;
	fdt32_t reg[2];
	int node, len;

	if (!fdt || fdt_check_header(fdt))
		goto invalid;
	node = fdt_path_offset(fdt, "/memory@50000000");
	if (node < 0)
		goto invalid;
	old = fdt_getprop(fdt, node, "reg", &len);
	if (!old || len != sizeof(reg) || fdt32_to_cpu(old[0]) != S31_PSRAM_BASE)
		goto invalid;
	reg[0] = cpu_to_fdt32(S31_PSRAM_BASE);
	reg[1] = cpu_to_fdt32(psram_size_bytes());
	if (fdt_setprop_inplace(fdt, node, "reg", reg, sizeof(reg)))
		goto invalid;
	return;
invalid:
	puts("spl: cannot update firmware PSRAM memory bank\n");
	hang();
}
