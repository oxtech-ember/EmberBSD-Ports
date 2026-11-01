// SPDX-License-Identifier: GPL-2.0+
/*
 * Opt-in U-Boot command for the ESP32-S31 Mosaico LCD diagnostic.
 */

#include <command.h>
#include <linux/errno.h>
#include <linux/delay.h>
#include <asm/io.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "mosaico_splash_core.h"

static uint32_t
mosaico_read32(void *cookie, uintptr_t address)
{
	(void)cookie;
	return readl((const void *)address);
}

static void
mosaico_write32(void *cookie, uintptr_t address, uint32_t value)
{
	(void)cookie;
	writel(value, (void *)address);
}

static uint32_t
mosaico_time_ms(void *cookie)
{
	(void)cookie;
	return (uint32_t)get_timer(0);
}

static void
mosaico_delay_us(void *cookie, uint32_t usec)
{
	(void)cookie;
	udelay(usec);
}

static int do_mosaico_splash(struct cmd_tbl *cmdtp, int flag, int argc,
    char *const argv[])
{
	static const struct mosaico_splash_io io = {
		.read32 = mosaico_read32,
		.write32 = mosaico_write32,
		.time_ms = mosaico_time_ms,
		.delay_us = mosaico_delay_us,
	};
	int error;

	(void)cmdtp;
	(void)flag;
	if (argc != 2 || strcmp(argv[1], "red") != 0)
		return CMD_RET_USAGE;

	error = mosaico_splash_run(&io, 0xf800);
	if (error != 0) {
		printf("Mosaico splash diagnostic failed (%d)\n", error);
		return CMD_RET_FAILURE;
	}
	puts("Mosaico red-field diagnostic sent\n");
	return CMD_RET_SUCCESS;
}

U_BOOT_CMD(
	mosaicosplash, 2, 0, do_mosaico_splash,
	"send a solid-color field to the Mosaico LCD (diagnostic only)",
	"red"
);
