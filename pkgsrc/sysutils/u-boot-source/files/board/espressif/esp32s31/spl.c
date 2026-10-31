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
#include <u-boot/crc.h>
#include <asm/io.h>
#include <asm/arch-esp32s31/rom.h>
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

#if IS_ENABLED(CONFIG_ESP32S31_NOR_MAP)
	/* ROM slow-read setup with the strapped flash pads. */
	puts("spl: ROM flash attach begin\n");
	esp_rom_spiflash_attach(0, false);
	puts("spl: ROM flash attach done\n");
#endif

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

	/* Complete CPU and systimer clock-tree bring-up after PSRAM.
	 */
	s31_spl_cpu_switch_to_cpll();
	s31_spl_systimer_clk_init();
#if IS_ENABLED(CONFIG_ESP32S31_NOR_PROBE)
	/* This probe reads mapped NOR only; it never changes flash state. */
	printf("NOR read probe: offset 00002000 length 00001000 crc32 %08x\n",
	       crc32(0, (const unsigned char *)0x40002000UL, 0x1000));
	printf("NOR read probe: offset 00020000 length 00001000 crc32 %08x\n",
	       crc32(0, (const unsigned char *)0x40020000UL, 0x1000));
#endif
#if IS_ENABLED(CONFIG_ESP32S31_NOR_BOOT)
	puts("ESP32-S31 PSRAM ready; trying NOR then UART FIT\n");
#else
	puts("ESP32-S31 PSRAM ready; waiting for UART FIT\n");
#endif
}

u32 spl_boot_device(void)
{
	return BOOT_DEVICE_UART;
}

#if CONFIG_IS_ENABLED(NOR_SUPPORT)
#define S31_NOR_WINDOW 0x40000000UL
#define S31_NOR_SIZE   0x01000000UL
#define S31_NOR_FIT    0x00020000UL

unsigned long spl_nor_get_uboot_base(void)
{
	return S31_NOR_WINDOW + S31_NOR_FIT;
}

bool spl_nor_get_bounds(ulong *start, ulong *size)
{
	*start = S31_NOR_WINDOW;
	*size = S31_NOR_SIZE;
	return true;
}
#endif

void board_boot_order(u32 *boot_list)
{
#if CONFIG_IS_ENABLED(NOR_SUPPORT) && IS_ENABLED(CONFIG_ESP32S31_NOR_BOOT)
	boot_list[0] = BOOT_DEVICE_NOR;
	boot_list[1] = BOOT_DEVICE_UART;
#else
	boot_list[0] = BOOT_DEVICE_UART;
#endif
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
