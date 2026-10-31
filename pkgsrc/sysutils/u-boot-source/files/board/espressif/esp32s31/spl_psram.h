/* SPDX-License-Identifier: GPL-2.0+ */
/*
 * ESP32-S31 PSRAM bring-up. Brings up an Octal PSRAM end-to-end:
 * LDO + MPLL + MSPI controller + mode regs + AXI config + MMU map at
 * 0x50000000. Verified on real silicon to be R/W via `md.l` / `mw.l` /
 * `mtest`. Returns 0 on success, -1 if the chip didn't respond to
 * mode-register readback.
 */

#ifndef _S31_SPL_PSRAM_H_
#define _S31_SPL_PSRAM_H_

#include <linux/types.h>

/*
 * The PSRAM mapping starts here and spans the capacity detected by
 * psram_init from the device mode register.
 */
#define PSRAM_VADDR_START 0x50000000UL

int psram_init(void);
u32 psram_size_bytes(void);

#endif /* _S31_SPL_PSRAM_H_ */
