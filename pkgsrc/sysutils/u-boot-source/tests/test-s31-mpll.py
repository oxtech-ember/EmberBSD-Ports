#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the S31 SPL MPLL register sequence with a simulated MMIO bus."""
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run

args = arguments(__doc__)
board = args.source / 'board/espressif/esp32s31'
clock = (board / 'spl_clk.c').read_text()
clock = clock[clock.index('#define ESP32S31_PMU_BASE'):clock.index('/*\n * Switch CPU')]
poll = (board / 'spl_poll.h').read_text()
psram = (board / 'spl_psram.c').read_text()
init = psram[psram.index('int psram_init(void)'):]
assert init.count('s31_spl_mpll_enable()') == 1
assert init.index('psram_ldo_init()') < init.index('s31_spl_mpll_enable()')
assert init.index('s31_spl_mpll_enable()') < init.index('psram_mspi_clock_init()')
psram = psram[psram.index('#define DR_REG_PMU_BASE'):psram.index('/* The shared SPL')]
source = r'''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define MAX_EVENTS 128
#define ANA_BASE 0x2010f800U
#define ANA_CONF1 (ANA_BASE + 0x1c)
#define ANA_CONF2 (ANA_BASE + 0x20)
#define DIV_REG 0x20701054U
#define CAL_REG 0x20587174U
struct event {
	uintptr_t address;
	u32 value;
};
static struct event events[MAX_EVENTS];
static unsigned int count, selected;
static u32 analog[256], ctrl_value, div_value, cal_value, initial_selector;
static bool busy_stuck, cal_stuck;
static unsigned int transactions, stall_after;

static u32
readl(const void *p)
{
	uintptr_t a = (uintptr_t)p;
	if (a == ANA_CONF2)
		return initial_selector ? BIT(16) : 0;
	if (a == ANA_BASE || a == ANA_BASE + 4)
		return ctrl_value | (busy_stuck ? BIT(25) : 0);
	if (a == DIV_REG)
		return div_value;
	if (a == CAL_REG)
		return cal_value | (cal_stuck ? 0 : BIT(8));
	return 0;
}

static void
writel(u32 value, void *p)
{
	uintptr_t a = (uintptr_t)p;
	assert(count < MAX_EVENTS);
	events[count++] = (struct event){ a, value };
	if (a == ANA_BASE || a == ANA_BASE + 4) {
		u32 reg = (value >> 8) & 0xff;
		assert(a == ANA_BASE + selected * 4);
		transactions++;
		if (stall_after && transactions == stall_after)
			busy_stuck = true;
		if (value & BIT(24))
			analog[reg] = (value >> 16) & 0xff;
		ctrl_value = analog[reg] << 16;
	} else if (a == DIV_REG) {
		div_value = value;
	} else if (a == CAL_REG) {
		cal_value = value & ~BIT(8);
	}
}

static void
setbits_le32(void *p, u32 bits)
{
	writel(readl(p) | bits, p);
}
'''
source += poll
source += clock
source += psram
source += r'''
static void
run_case(bool conf2_set)
{
	unsigned int i, n = 0, selections = 0;
	u32 writes[4] = {0};
	u32 addresses[4] = {0};
	int second_write = -1, div9 = -1, third_write = -1, fourth_write = -1;
	int start = -1, div24 = -1, stop = -1;

	memset(events, 0, sizeof(events));
	memset(analog, 0, sizeof(analog));
	count = 0;
	initial_selector = conf2_set;
	selected = conf2_set ? 0 : 1;
	ctrl_value = div_value = cal_value = 0;
	transactions = stall_after = 0;
	analog[1] = 0x80;
	analog[3] = 0xc0;
	busy_stuck = cal_stuck = false;
	assert(s31_spl_mpll_enable() == 0);
	for (i = 0; i < count; i++) {
		struct event e = events[i];
		assert(e.address != 0x207041e8U); /* PSRAM rail belongs to LDO. */
		if (e.address == ANA_CONF1) {
			assert(e.value == ((~BIT(14)) & 0xffffff));
			selections++;
		}
		if (e.address == ANA_BASE + selected * 4 && (e.value & BIT(24))) {
			assert(n < 4);
			addresses[n] = (e.value >> 8) & 0xff;
			writes[n++] = (e.value >> 16) & 0xff;
			if (n == 2)
				second_write = i;
			if (n == 3)
				third_write = i;
			if (n == 4)
				fourth_write = i;
		}
		if (e.address == DIV_REG && ((e.value >> 3) & 31) == 9)
			div9 = i;
		if (e.address == DIV_REG && ((e.value >> 3) & 31) == 24)
			div24 = i;
		if (e.address == CAL_REG && !(e.value & BIT(9)))
			start = i;
		if (e.address == CAL_REG && (e.value & BIT(9)))
			stop = i;
	}
	assert(n == 4);
	assert(selections == 8);
	assert(addresses[0] == 1 && writes[0] == 0x83);
	assert(addresses[1] == 1 && writes[1] == 0x87);
	assert(addresses[2] == 3 && writes[2] == 0xf0);
	assert(addresses[3] == 1 && writes[3] == 0x83);
	assert(second_write >= 0 && second_write < div9);
	assert(div9 < third_write && third_write < fourth_write);
	assert(fourth_write < start && start < div24 && div24 < stop);
}

int
main(void)
{
	unsigned int phase;

	run_case(false);
	run_case(true);
	count = 0;
	psram_ldo_init();
	assert(count == 2);
	assert(events[0].address == 0x20704218U && events[0].value == 424U);
	assert(events[1].address == 0x207041e8U && events[1].value == BIT(31));
	count = 0;
	busy_stuck = true;
	assert(s31_spl_mpll_enable() != 0);
	for (phase = 1; phase <= 2; phase++) {
		count = transactions = 0;
		busy_stuck = false;
		stall_after = phase;
		assert(s31_spl_mpll_enable() != 0);
		assert(transactions == phase);
	}
	busy_stuck = false;
	stall_after = 0;
	cal_stuck = true;
	count = 0;
	assert(s31_spl_mpll_enable() != 0);
	assert(cal_value & BIT(9));
	puts("S31 MPLL register sequence passed for both analog controllers");
	return 0;
}
'''
compile_and_run(args, source, cflags=('-Wall', '-Wextra', '-Werror'))
