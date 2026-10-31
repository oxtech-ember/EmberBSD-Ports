/* SPDX-License-Identifier: GPL-2.0+ */
#ifndef _S31_SPL_POLL_H_
#define _S31_SPL_POLL_H_

/* Iteration bound: early SPL has not yet initialised a reliable timer. */
#define S31_POLL_LIMIT 1000000U

static inline bool s31_poll_register(const void *reg, u32 mask, u32 expected)
{
	u32 poll;

	for (poll = 0; poll < S31_POLL_LIMIT; poll++) {
		if ((readl(reg) & mask) == expected)
			return true;
	}
	return false;
}

#endif /* _S31_SPL_POLL_H_ */
