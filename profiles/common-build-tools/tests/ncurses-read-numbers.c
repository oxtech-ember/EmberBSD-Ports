/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test actual ncurses numeric decoding. */
#ifndef EMBERBSD_NCURSES_READ_ENTRY_SOURCE
#error Define EMBERBSD_NCURSES_READ_ENTRY_SOURCE to the actual read_entry.c.
#endif
#include EMBERBSD_NCURSES_READ_ENTRY_SOURCE
#include <limits.h>

#if !NCURSES_EXT_NUMBERS
#error Use the configured extended-number ncurses build.
#endif

int
main(void)
{
    static const unsigned char input16[][2] = {
	{ 0, 0 }, { 1, 0 }, { 255, 127 },
	{ 0, 128 }, { 254, 255 }, { 255, 255 }
    };
    static const int expected16[] = { 0, 1, 32767, -32768, -2, -1 };
    static const unsigned char input32[][4] = {
	{ 0, 0, 0, 0 }, { 1, 0, 0, 0 }, { 255, 127, 0, 0 },
	{ 255, 255, 0, 0 }, { 0, 0, 1, 0 }, { 255, 255, 255, 127 },
	{ 0, 0, 0, 128 }, { 254, 255, 255, 255 }, { 255, 255, 255, 255 }
    };
    static const int expected32[] = {
	0, 1, 32767, 65535, 65536, INT_MAX, INT_MIN, -2, -1
    };
    NCURSES_INT2 actual16[6], actual32[9];
    size_t i;

    if (sizeof(NCURSES_INT2) != 4 || sizeof(int) != 4)
	return 2;
    if (convert_16bits((const char *)input16, actual16, 6) != 2 ||
	convert_32bits((const char *)input32, actual32, 9) != 4)
	return 3;
    for (i = 0; i < 6; i++) {
	if (actual16[i] != expected16[i])
	    return 4;
    }
    for (i = 0; i < 9; i++) {
	if (actual32[i] != expected32[i])
	    return 5;
    }
    puts("PASS: 15 real ncurses numeric boundary values");
    return 0;
}
