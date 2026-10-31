/* SPDX-License-Identifier: MIT */
#ifndef LV_CONF_H
#define LV_CONF_H

/* Use the OS C library rather than embedded allocator/stdio copies. */
#define LV_USE_STDLIB_MALLOC LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_CLIB
#define LV_USE_OS LV_OS_NONE
#define LV_COLOR_FORMAT_DEFAULT LV_COLOR_FORMAT_RGB565
#define LV_USE_DRAW_SW 1
#define LV_USE_THORVG 0
#define LV_USE_VECTOR_GRAPHIC 0
#define LV_USE_FLOAT 0
#define LV_USE_LODEPNG 0
#define LV_USE_LIBPNG 0
#define LV_USE_TJPGD 0
#define LV_USE_LIBJPEG_TURBO 0
#define LV_USE_LIBWEBP 0
#define LV_USE_LZ4 0
#define LV_USE_FREETYPE 0
#define LV_USE_TINY_TTF 0
#define LV_USE_SDL 0
#define LV_USE_LINUX_DRM 0
#define LV_USE_LINUX_FBDEV 0
#define LV_USE_EVDEV 0

#endif
