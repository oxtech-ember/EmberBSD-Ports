/* SPDX-License-Identifier: GPL-2.0+ */
#ifndef __S31_PSRAM_LAYOUT_H
#define __S31_PSRAM_LAYOUT_H

#define S31_PSRAM_BASE          0x50000000U
#define S31_PSRAM_MIN_SIZE      0x01000000U
#define S31_PSRAM_RELOC_TOP     0x51000000U
#define S31_PSRAM_RUNTIME_FLOOR 0x50f70000U
#define S31_PSRAM_STACK_MARGIN  0x00020000U

static inline int s31_psram_size_supported(unsigned int size)
{
	return size == 0x01000000U || size == 0x02000000U ||
	       size == 0x04000000U;
}

#endif
