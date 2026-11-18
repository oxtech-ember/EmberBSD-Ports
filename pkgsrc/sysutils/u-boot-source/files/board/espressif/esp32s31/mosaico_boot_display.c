// SPDX-License-Identifier: GPL-2.0+
/* EmberBSD boot presentation for the Mosaico CO5300 panel. */
#include <asm/global_data.h>
#include <bootstage.h>
#include <linux/string.h>
#include <video_font_8x16.h>

#include "mosaico_splash_core.h"
#include "emberbsd_boot_logo.h"

DECLARE_GLOBAL_DATA_PTR;

#define PANEL_WIDTH 480
#define TEXT_WIDTH 384
#define FONT_SCALE 2
#define LOGO_SCALE 3

static bool display_active;

static int
draw_logo(void)
{
	const unsigned int width = BOOT_LOGO_WIDTH * LOGO_SCALE;
	uint8_t pair[2 * BOOT_LOGO_WIDTH * LOGO_SCALE * 2];
	unsigned int x, y, row;

	for (y = 0; y < BOOT_LOGO_HEIGHT * LOGO_SCALE; y += 2) {
		uint8_t *p = pair;

		for (row = y; row < y + 2; row++) {
			for (x = 0; x < width; x++) {
				unsigned int pixel = (row / LOGO_SCALE) *
				    BOOT_LOGO_WIDTH + x / LOGO_SCALE;
				uint8_t byte = boot_logo_pixels[pixel / 2];
				uint16_t rgb = boot_logo_palette[pixel & 1 ?
				    byte & 15 : byte >> 4];
				*p++ = rgb >> 8;
				*p++ = rgb;
			}
		}
		if (mosaico_splash_write_pair(&mosaico_panel_io,
		    (PANEL_WIDTH - width) / 2, 64 + y, width, pair))
			return -1;
	}
	return 0;
}

/* Replace a whole text line, including the ends of the previous message. */
static int
draw_text(const char *text, unsigned int top, uint16_t fg)
{
	const size_t length = strlen(text);
	uint8_t pair[2 * TEXT_WIDTH * 2];
	unsigned int left, x, y;

	if (length > TEXT_WIDTH / (8 * FONT_SCALE))
		return -1;
	left = (TEXT_WIDTH - length * 8 * FONT_SCALE) / 2;
	for (y = 0; y < 16; y++) {
		memset(pair, 0, sizeof(pair));
		for (x = 0; x < length * 8 * FONT_SCALE; x++) {
			unsigned int col = x / FONT_SCALE;
			unsigned char c = text[col / 8];
			if (video_fontdata_8x16[c * 16 + y] & (0x80 >> (col % 8))) {
				pair[(left + x) * 2] = fg >> 8;
				pair[(left + x) * 2 + 1] = fg;
			}
		}
		memcpy(pair + TEXT_WIDTH * 2, pair, TEXT_WIDTH * 2);
		if (mosaico_splash_write_pair(&mosaico_panel_io,
		    (PANEL_WIDTH - TEXT_WIDTH) / 2, top + y * 2, TEXT_WIDTH, pair))
			return -1;
	}
	return 0;
}

void
mosaico_boot_display_init(void)
{
	display_active = mosaico_splash_run(&mosaico_panel_io, 0) == 0 &&
	    draw_logo() == 0 && draw_text("EmberBSD", 296, 0xffff) == 0 &&
	    draw_text("U-Boot", 356, 0xfd8a) == 0;
}

void
show_boot_progress(int stage)
{
	const char *text;

	if (!(gd->flags & GD_FLG_RELOC) || !display_active)
		return;
	switch (stage) {
	case BOOTSTAGE_ID_BOOTM_START:
		text = "Checking kernel image";
		break;
	case BOOTSTAGE_ID_KERNEL_LOADED:
		text = "Kernel loaded";
		break;
	case BOOTSTAGE_ID_RUN_OS:
		text = "Starting kernel";
		break;
	default:
		if (stage >= 0)
			return;
		text = "Boot error - see UART";
	}
	if (draw_text(text, 356, stage < 0 ? 0xf986 : 0xfd8a))
		display_active = false;
}
