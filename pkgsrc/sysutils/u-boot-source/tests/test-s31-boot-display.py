#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the production S31 Mosaico boot display renderer."""
import struct
import sys
import tempfile
import zlib
from pathlib import Path
from shutil import copyfile

sys.dont_write_bytecode = True
from common import arguments, compile_and_run


def configure(parser):
    parser.add_argument('--preview', type=Path,
                        help='write the rendered framebuffer as a PNG')


args = arguments(__doc__, configure)
if not (args.source / 'include/video_font_8x16.h').is_file():
    raise SystemExit('selected U-Boot source has no real 8x16 font header')

program = r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <video_font_8x16.h>
#include "mosaico_boot_display.c"

#define WIDTH 480U
#define HEIGHT 480U
#define STRIDE (WIDTH * 2U)
#define PIXELS (WIDTH * HEIGHT * 2U)

struct global_data test_gd;
struct global_data *gd = &test_gd;
const struct mosaico_splash_io mosaico_panel_io = {0};

static uint8_t framebuffer[PIXELS];
static unsigned int pair_calls, run_calls, fail_pair;
static int panel_error;

int
mosaico_splash_run(const struct mosaico_splash_io *io, uint16_t color)
{
	(void)io;
	(void)color;
	run_calls++;
	if (panel_error)
		return -1;
	memset(framebuffer, 0, sizeof(framebuffer));
	return 0;
}

int
mosaico_splash_write_pair(const struct mosaico_splash_io *io,
	unsigned int x, unsigned int y, unsigned int width,
	const uint8_t *pixels)
{
	(void)io;
	assert(pixels != NULL && width != 0 && (width & 3U) == 0);
	assert(x <= WIDTH - width && y <= HEIGHT - 2U && (y & 1U) == 0);
	pair_calls++;
	if (fail_pair != 0 && pair_calls == fail_pair)
		return -1;
	memcpy(framebuffer + y * STRIDE + x * 2U, pixels, width * 2U);
	memcpy(framebuffer + (y + 1U) * STRIDE + x * 2U,
	    pixels + width * 2U, width * 2U);
	return 0;
}

static void
put_pixel(uint8_t *image, unsigned int x, unsigned int y, uint16_t color)
{
	size_t offset = y * STRIDE + x * 2U;

	image[offset] = color >> 8;
	image[offset + 1U] = color;
}

static void
expected_logo(uint8_t *image)
{
	unsigned int x, y;

	for (y = 0; y < BOOT_LOGO_HEIGHT * LOGO_SCALE; y++) {
		for (x = 0; x < BOOT_LOGO_WIDTH * LOGO_SCALE; x++) {
			unsigned int pixel = (y / LOGO_SCALE) * BOOT_LOGO_WIDTH +
			    x / LOGO_SCALE;
			uint8_t packed = boot_logo_pixels[pixel / 2U];
			uint16_t color = boot_logo_palette[(pixel & 1U) ?
			    packed & 15U : packed >> 4];

			put_pixel(image, (WIDTH - BOOT_LOGO_WIDTH * LOGO_SCALE) / 2U +
			    x, 64U + y, color);
		}
	}
}

static void
expected_text(uint8_t *image, const char *text, unsigned int top,
	uint16_t foreground)
{
	size_t length = strlen(text);
	unsigned int left, col, row, sx, sy;

	assert(length <= TEXT_WIDTH / (8U * FONT_SCALE));
	for (row = 0; row < 16U * FONT_SCALE; row++)
		memset(image + (top + row) * STRIDE +
		    (WIDTH - TEXT_WIDTH) / 2U * 2U, 0, TEXT_WIDTH * 2U);
	left = (TEXT_WIDTH - (unsigned int)length * 8U * FONT_SCALE) / 2U;
	for (row = 0; row < 16U; row++) {
		for (col = 0; col < length * 8U; col++) {
			unsigned char ch = (unsigned char)text[col / 8U];
			uint16_t color = (video_fontdata_8x16[ch * 16U + row] &
			    (0x80U >> (col & 7U))) ? foreground : 0;

			for (sy = 0; sy < FONT_SCALE; sy++) {
				for (sx = 0; sx < FONT_SCALE; sx++) {
					put_pixel(image, (WIDTH - TEXT_WIDTH) / 2U + left +
					    col * FONT_SCALE + sx,
					    top + row * FONT_SCALE + sy, color);
				}
			}
		}
	}
}

static void
assert_frame(const uint8_t *expected)
{
	assert(memcmp(framebuffer, expected, PIXELS) == 0);
}

static void
check_initial_frame(uint8_t *expected)
{
	memset(expected, 0, PIXELS);
	expected_logo(expected);
	expected_text(expected, "EmberBSD", 296U, 0xffffU);
	expected_text(expected, "U-Boot", 356U, 0xfd8aU);
	assert_frame(expected);
}

int
main(int argc, char **argv)
{
	uint8_t expected[PIXELS];
	unsigned int before;
	FILE *preview;

	assert(argc == 2);
	pair_calls = run_calls = 0;
	panel_error = 0;
	fail_pair = 0;
	test_gd.flags = 0;
	mosaico_boot_display_init();
	assert(run_calls == 1 && pair_calls == 140U);
	check_initial_frame(expected);

	/* Before relocation, ordinary positive boot stages do not touch the LCD. */
	before = pair_calls;
	show_boot_progress(BOOTSTAGE_ID_BOOTM_START);
	assert(pair_calls == before);
	assert_frame(expected);

	/* Positive non-display stages are filtered; visible messages replace the
	 * complete U-Boot line and keep the logo intact. */
	test_gd.flags = GD_FLG_RELOC;
	show_boot_progress(99);
	assert(pair_calls == before && memcmp(framebuffer, expected, PIXELS) == 0);
	show_boot_progress(BOOTSTAGE_ID_BOOTM_START);
	expected_text(expected, "Checking kernel image", 356U, 0xfd8aU);
	assert(pair_calls == before + 16U);
	assert_frame(expected);
	before = pair_calls;
	show_boot_progress(BOOTSTAGE_ID_KERNEL_LOADED);
	expected_text(expected, "Kernel loaded", 356U, 0xfd8aU);
	assert(pair_calls == before + 16U);
	assert_frame(expected);
	before = pair_calls;
	show_boot_progress(BOOTSTAGE_ID_RUN_OS);
	expected_text(expected, "Starting kernel", 356U, 0xfd8aU);
	assert(pair_calls == before + 16U);
	assert_frame(expected);
	before = pair_calls;
	show_boot_progress(-1);
	expected_text(expected, "Boot error - see UART", 356U, 0xf986U);
	assert(pair_calls == before + 16U);
	assert_frame(expected);

	/* Panel or transfer failure disables display output without stopping boot. */
	panel_error = 1;
	pair_calls = run_calls = 0;
	mosaico_boot_display_init();
	assert(run_calls == 1 && pair_calls == 0);
	show_boot_progress(BOOTSTAGE_ID_RUN_OS);
	assert(pair_calls == 0);
	panel_error = 0;
	fail_pair = 1;
	pair_calls = run_calls = 0;
	mosaico_boot_display_init();
	assert(run_calls == 1 && pair_calls == 1);
	show_boot_progress(BOOTSTAGE_ID_RUN_OS);
	assert(pair_calls == 1);

	/* Re-render a real stage and export exactly the bytes sent to the mock. */
	fail_pair = 0;
	pair_calls = run_calls = 0;
	mosaico_boot_display_init();
	test_gd.flags = GD_FLG_RELOC;
	show_boot_progress(BOOTSTAGE_ID_RUN_OS);
	expected_text(expected, "Starting kernel", 356U, 0xfd8aU);
	assert_frame(expected);
	preview = fopen(argv[1], "wb");
	assert(preview != NULL);
	assert(fwrite(framebuffer, 1, PIXELS, preview) == PIXELS);
	assert(fclose(preview) == 0);
	puts("S31 Mosaico boot display pixels, stages and fail-open passed");
	return 0;
}
'''


def png_chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))


def write_preview(raw, destination):
    if len(raw) != 480 * 480 * 2:
        raise ValueError('mock renderer produced an unexpected framebuffer size')
    pixels = bytearray()
    for offset in range(0, len(raw), 2):
        value = (raw[offset] << 8) | raw[offset + 1]
        red = (value >> 11) & 0x1f
        green = (value >> 5) & 0x3f
        blue = value & 0x1f
        pixels.extend(((red * 255 + 15) // 31,
                       (green * 255 + 31) // 63,
                       (blue * 255 + 15) // 31))
    rows = b''.join(b'\0' + pixels[y * 480 * 3:(y + 1) * 480 * 3]
                    for y in range(480))
    header = struct.pack('>IIBBBBB', 480, 480, 8, 2, 0, 0, 0)
    output = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) +
              png_chunk(b'IDAT', zlib.compress(rows, 9)) +
              png_chunk(b'IEND', b''))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(output)


with tempfile.TemporaryDirectory(prefix='s31-boot-display-') as directory:
    temp = Path(directory)
    stub = temp / 'stub'
    (stub / 'asm').mkdir(parents=True)
    (stub / 'linux').mkdir()
    font = temp / 'font'
    font.mkdir()
    copyfile(args.source / 'include/video_font_8x16.h',
             font / 'video_font_8x16.h')
    copyfile(args.source / 'include/video_font_data.h',
             font / 'video_font_data.h')
    (stub / 'asm/global_data.h').write_text('''#ifndef TEST_GLOBAL_DATA_H
#define TEST_GLOBAL_DATA_H
struct global_data { unsigned long flags; };
extern struct global_data *gd;
#define DECLARE_GLOBAL_DATA_PTR extern struct global_data *gd
#define GD_FLG_RELOC (1UL << 1)
#endif
''')
    (stub / 'bootstage.h').write_text('''#define BOOTSTAGE_ID_BOOTM_START 11
#define BOOTSTAGE_ID_KERNEL_LOADED 12
#define BOOTSTAGE_ID_RUN_OS 13
''')
    (stub / 'linux/string.h').write_text('#include <string.h>\n')
    raw_path = temp / 'framebuffer.rgb565'
    compile_and_run(
        args, program,
        include=(stub, font,
                 args.source / 'board/espressif/esp32s31'),
        cflags=('-Wall', '-Wextra', '-Werror'),
        run_args=(raw_path,))
    if args.preview is not None:
        write_preview(raw_path.read_bytes(), args.preview)
        print(f'PNG preview written: {args.preview}')
