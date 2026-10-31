/* SPDX-License-Identifier: MIT */
/* A memory-only partial-rendering smoke test; no device or OS backend. */
#include <lvgl/lvgl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define WIDTH 64
#define HEIGHT 64
static uint16_t drawbuf[WIDTH * 8];
static uint16_t pixels[WIDTH * HEIGHT];
static unsigned int flushes;
static int bad_area;

static void
flush(lv_display_t *display, const lv_area_t *area, uint8_t *data)
{
    int y;
    unsigned int width;

    if (area->x1 < 0 || area->y1 < 0 || area->x2 >= WIDTH ||
        area->y2 >= HEIGHT || area->x1 > area->x2 || area->y1 > area->y2) {
        bad_area = 1;
        lv_display_flush_ready(display);
        return;
    }
    width = (unsigned int)(area->x2 - area->x1 + 1);
    for (y = area->y1; y <= area->y2; y++) {
        memcpy(&pixels[y * WIDTH + area->x1], data, width * sizeof(uint16_t));
        data += width * sizeof(uint16_t);
    }
    flushes++;
    lv_display_flush_ready(display);
}

int
main(void)
{
    lv_display_t *display;
    lv_obj_t *label;
    unsigned int i, changed = 0, distinct = 0;

    lv_init();
    display = lv_display_create(WIDTH, HEIGHT);
    if (display == NULL)
        return 1;
    lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(display, drawbuf, NULL, sizeof(drawbuf),
        LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(display, flush);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_hex(0x336699), 0);
    label = lv_label_create(lv_screen_active());
    lv_label_set_text(label, "EmberBSD");
    lv_refr_now(display);
    for (i = 0; i < WIDTH * HEIGHT; i++)
        if (pixels[i] != 0)
            changed++;
    for (i = 1; i < WIDTH * HEIGHT; i++)
        if (pixels[i] != pixels[0])
            distinct++;
    if (bad_area || flushes < 2 || changed == 0 || distinct == 0) {
        fprintf(stderr, "render failed: area=%d flushes=%u pixels=%u\n",
            bad_area, flushes, changed);
        return 1;
    }
    printf("RGB565 partial rendering: %u flushes, %u pixels\n", flushes, changed);
    lv_deinit();
    return 0;
}
