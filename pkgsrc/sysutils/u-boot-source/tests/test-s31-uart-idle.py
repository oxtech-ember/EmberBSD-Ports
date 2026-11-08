# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Check S31 serial init waits for the UART shifter, not only its FIFO."""
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run

args = arguments(__doc__)
driver_path = args.source / 'drivers/serial/serial_esp.c'
header_path = (args.source /
               'arch/riscv/include/asm/arch-esp32s31/soc/uart_reg.h')
driver = driver_path.read_text()
header = header_path.read_text()


def extract_braced(source, marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    for end in range(opening, len(source)):
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
            if depth == 0:
                return source[start:end + 1]
    raise ValueError(f'unterminated source block: {marker}')


def define(name):
    match = re.search(rf'^#define\s+{name}\b.*$', header, re.M)
    if match is None:
        raise ValueError(f'missing UART register definition: {name}')
    return match.group(0)


uart_struct = extract_braced(driver, 'struct uart_esp') + ';'
tx_pending = ''
if 'static u32 _esp_serial_tx_pending(' in driver:
    tx_pending = extract_braced(driver, 'static u32 _esp_serial_tx_pending(')
serial_init = extract_braced(driver, 'static void _esp_serial_init(')
update_macro = re.search(r'^#define\s+UART_UPDATE_OFF\s+.*$', driver, re.M)
if update_macro is None:
    raise ValueError('missing UART update register offset')

register_defines = '\n'.join(define(name) for name in (
    'UART_TXFIFO_CNT_M', 'UART_TXFIFO_CNT_S', 'UART_TXFIFO_RST',
    'UART_RXFIFO_RST', 'UART_FSM_STATUS_OFF', 'UART_ST_UTX_OUT_M',
    'UART_ST_UTX_OUT_S'))

source = r'''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
''' + register_defines + '\n' + update_macro.group(0) + '\n' + uart_struct + r'''

static struct uart_esp *test_regs;
static unsigned int fsm_reads;
static unsigned int busy_reads;
static u32 last_fsm_state;
static u32 sync_value;
static unsigned int sync_writes;
static unsigned int update_writes;

static u32
readl(const void *address)
{
	uintptr_t fsm_address = (uintptr_t)test_regs + UART_FSM_STATUS_OFF;
	uintptr_t update_address = (uintptr_t)test_regs + UART_UPDATE_OFF;

	if (address == &test_regs->status)
		return 0; /* FIFO is empty throughout the case. */
	if ((uintptr_t)address == fsm_address) {
		last_fsm_state = fsm_reads++ < busy_reads ? 5U : 0U;
		return last_fsm_state << UART_ST_UTX_OUT_S;
	}
	if ((uintptr_t)address == update_address)
		return 0; /* Register update completes immediately. */
	if (address == &test_regs->sync)
		return sync_value;
	abort();
}

static void
writel(u32 value, void *address)
{
	uintptr_t update_address = (uintptr_t)test_regs + UART_UPDATE_OFF;

	if (address == &test_regs->sync) {
		if (value & (UART_TXFIFO_RST | UART_RXFIFO_RST))
			assert(last_fsm_state == 0);
		sync_value = value;
		sync_writes++;
		return;
	}
	if ((uintptr_t)address == update_address) {
		assert(value == 1);
		update_writes++;
		return;
	}
	abort();
}
''' + tx_pending + '\n' + serial_init + r'''

int
main(void)
{
	struct uart_esp regs = {0};
	test_regs = &regs;

''' + ('	busy_reads = UINT32_MAX;\n\tassert(_esp_serial_tx_pending(&regs) != 0);\n'
       if tx_pending else '') + r'''	/* FIFO stays empty; the transmitter is busy once, then becomes idle. */
	fsm_reads = 0;
	busy_reads = 1;
	last_fsm_state = 5;
	_esp_serial_init(&regs);
	assert(fsm_reads == 2);
	assert(sync_writes == 2);
	assert(update_writes == 2);
	puts("S31 UART waits for FIFO and TX FSM idle before reset: passed");
	return 0;
}
'''

compile_and_run(args, source, cflags=('-Wall', '-Wextra', '-Werror'))
