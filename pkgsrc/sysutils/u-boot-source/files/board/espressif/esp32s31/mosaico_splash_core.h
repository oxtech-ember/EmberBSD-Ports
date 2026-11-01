/* SPDX-License-Identifier: Apache-2.0 */
/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 * Mosaico ESP32-S31 opt-in LCD diagnostic.
 * The panel sequence is adapted from Espressif Mosaico Claw
 * mosaico_boot_splash.c (Apache-2.0), commit
 * 2654a4a9f76f5d7ea108e4dff7ade7b1df4c1c5c.
 */

#ifndef __ESP32S31_MOSAICO_SPLASH_CORE_H
#define __ESP32S31_MOSAICO_SPLASH_CORE_H

#ifdef __UBOOT__
#include <linux/types.h>
#else
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#endif

struct mosaico_splash_io {
	void *cookie;
	uint32_t (*read32)(void *cookie, uintptr_t address);
	void (*write32)(void *cookie, uintptr_t address, uint32_t value);
	uint32_t (*time_ms)(void *cookie);
	void (*delay_us)(void *cookie, uint32_t usec);
};

int mosaico_splash_run(const struct mosaico_splash_io *io, uint16_t rgb565);

#endif
