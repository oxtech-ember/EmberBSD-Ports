#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the production S31 Mosaico SPI/GPIO sequence on simulated MMIO."""
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run

args = arguments(__doc__)
core = args.source / 'board/espressif/esp32s31/mosaico_splash_core.c'
program = f'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "{core}"

#define GPIO_BASE 0x20583000U
#define IOMUX_BASE 0x20582000U
#define GPIO_MATRIX_OUT_BASE (GPIO_BASE + 0xaf4U)
#define CLK_BASE 0x20587000U
#define SPI_BASE 0x2038f000U
#define REG_CMD (SPI_BASE + 0x00U)
#define REG_CTRL (SPI_BASE + 0x08U)
#define REG_USER (SPI_BASE + 0x10U)
#define REG_DLEN (SPI_BASE + 0x1cU)
#define REG_MISC (SPI_BASE + 0x20U)
#define REG_FIFO (SPI_BASE + 0x98U)
#define TEST_SPI_USR (1U << 24)
#define TEST_SPI_UPDATE (1U << 23)
#define SPI_QUAD (1U << 13)
#define SPI_KEEP (1U << 30)
#define TEST_SPI_USER_MOSI (1U << 27)
#define SPI_DOUTDIN (1U << 0)
#define IOMUX_MCU_SEL_MASK (7U << 12)
#define TEST_PAD_FIELDS 0x0a00U
#define TEST_MATRIX_OE_SEL (1U << 10)
#define MAX_REGS 128
#define MAX_TX 24

struct reg {{ uintptr_t addr; uint32_t val; }};
struct tx {{ unsigned int bytes, lines; int keep; uint8_t first[8]; }};
struct mock {{
    struct reg regs[MAX_REGS]; unsigned int nregs;
    struct tx initial[MAX_TX], last, last_quad; unsigned int ntx, quad_count;
    uint8_t fifo[64]; uint32_t command; unsigned int now, delays[4], ndelays;
    int stall; unsigned int updates;
}};

static uint32_t getreg(struct mock *m, uintptr_t a) {{
    unsigned int i;
    for (i = 0; i < m->nregs; i++) if (m->regs[i].addr == a) return m->regs[i].val;
    return 0;
}}
static void setreg(struct mock *m, uintptr_t a, uint32_t v) {{
    unsigned int i;
    for (i = 0; i < m->nregs; i++) if (m->regs[i].addr == a) {{ m->regs[i].val = v; return; }}
    assert(m->nregs < MAX_REGS); m->regs[m->nregs++] = (struct reg){{a, v}};
}}
static uint32_t rd(void *cookie, uintptr_t a) {{
    struct mock *m = cookie;
    if (a == REG_CMD) return m->command;
    return getreg(m, a);
}}
static void wr(void *cookie, uintptr_t a, uint32_t v) {{
    struct mock *m = cookie;
    if (a >= REG_FIFO && a < REG_FIFO + 64U) {{
        unsigned int off = (unsigned int)(a - REG_FIFO), i;
        for (i = 0; i < 4; i++) m->fifo[off + i] = (uint8_t)(v >> (8U * i));
        return;
    }}
    if (a == REG_CMD) {{
        if (v & TEST_SPI_UPDATE) {{ m->updates++; m->command = m->stall == 1 ? TEST_SPI_UPDATE : 0; }}
        else if (v & TEST_SPI_USR) {{
            struct tx t;
            unsigned int i;
            memset(&t, 0, sizeof(t));
            assert((getreg(m, REG_DLEN) + 1U) % 8U == 0);
            t.bytes = (getreg(m, REG_DLEN) + 1U) / 8U;
            t.lines = (getreg(m, REG_USER) & SPI_QUAD) ? 4U : 1U;
            t.keep = (getreg(m, REG_MISC) & SPI_KEEP) != 0;
            assert((getreg(m, REG_USER) & TEST_SPI_USER_MOSI) != 0);
            assert((getreg(m, REG_USER) & SPI_DOUTDIN) == 0);
            assert(t.bytes > 0 && t.bytes <= sizeof(m->fifo));
            memcpy(t.first, m->fifo, sizeof(t.first));
            if (t.lines == 4) {{
                assert(t.bytes == 64U);
                assert((getreg(m, REG_CTRL) & ((1U << 15) | (0xfU << 18))) == ((1U << 15) | (0xfU << 18)));
                assert(t.keep == (m->quad_count < 7199U));
                for (i = 0; i < t.bytes; i += 2) assert(m->fifo[i] == 0xf8 && m->fifo[i + 1] == 0x00);
                m->quad_count++;
                m->last_quad = t;
            }} else {{
                assert((getreg(m, REG_CTRL) & (0xfU << 18)) == (0xfU << 18));
            }}
            if (m->ntx < MAX_TX) m->initial[m->ntx] = t;
            m->last = t; m->ntx++;
            m->command = m->stall == 2 ? TEST_SPI_USR : 0;
        }}
        return;
    }}
    if (a == GPIO_BASE + 0x38U || a == GPIO_BASE + 0x44U) {{
        setreg(m, a, getreg(m, a) | v); return;
    }}
    setreg(m, a, v);
}}
static uint32_t now_ms(void *cookie) {{ return ((struct mock *)cookie)->now++; }}
static void delay_us(void *cookie, uint32_t us) {{
    struct mock *m = cookie; assert(m->ndelays < 4); m->delays[m->ndelays++] = us;
}}

int main(void) {{
    struct mock m = {{0}};
    const struct mosaico_splash_io io = {{ &m, rd, wr, now_ms, delay_us }};
    static const uint8_t commands[][5] = {{
        {{2,0,0x11,0,0}}, {{2,0,0xfe,0,0x20}}, {{2,0,0x19,0,0x10}},
        {{2,0,0x1c,0,0xa0}}, {{2,0,0xfe,0,0}}, {{2,0,0xc4,0,0x80}},
        {{2,0,0x3a,0,0x55}}, {{2,0,0x53,0,0x20}}, {{2,0,0x51,0,0x66}},
        {{2,0,0x63,0,0xff}}, {{2,0,0x36,0,0}},
        {{2,0,0x2a,0,0}}, {{2,0,0x2b,0,0}}, {{0x32,0,0x2c,0,0}},
    }};
    static const unsigned int output_gpios[] = {{60, 44, 42, 36, 51, 35, 9, 50}};
    static const unsigned int output_signals[] = {{256, 256, 53, 55, 54, 57, 56, 62}};
    unsigned int i;

    for (i = 0; i < sizeof(output_gpios) / sizeof(output_gpios[0]); i++) {{
        unsigned int gpio = output_gpios[i];
        setreg(&m, IOMUX_BASE + gpio * 4U, TEST_PAD_FIELDS | (3U << 12));
        setreg(&m, GPIO_MATRIX_OUT_BASE + gpio * 4U, 0x12fU | (1U << 9));
    }}
    assert(mosaico_splash_run(&io, 0xf800) == 0);
    assert(m.ndelays == 3 && m.delays[0] == 10000 && m.delays[1] == 150000 && m.delays[2] == 60000);
    assert(m.ntx == 7215 && m.quad_count == 7200 && m.updates == m.ntx);
    for (i = 0; i < 14; i++) {{
        assert(m.initial[i].lines == 1);
        assert(memcmp(m.initial[i].first, commands[i], i == 11 || i == 12 ? 4 : 5) == 0);
    }}
    assert(m.initial[11].bytes == 8 && m.initial[12].bytes == 8);
    assert(m.initial[11].first[4] == 0 && m.initial[11].first[5] == 0 &&
        m.initial[11].first[6] == 1 && m.initial[11].first[7] == 0xdf);
    assert(m.initial[12].first[4] == 0 && m.initial[12].first[5] == 0 &&
        m.initial[12].first[6] == 1 && m.initial[12].first[7] == 0xdf);
    assert(m.initial[13].bytes == 4 && m.initial[13].keep);
    assert(m.initial[14].lines == 4 && m.initial[14].keep);
    assert(m.last_quad.lines == 4 && !m.last_quad.keep);
    assert(m.last.lines == 1 && m.last.bytes == 4 && !m.last.keep);
    assert(m.last.first[0] == 2 && m.last.first[2] == 0x29);
    for (i = 0; i < sizeof(output_gpios) / sizeof(output_gpios[0]); i++) {{
        unsigned int gpio = output_gpios[i];
        unsigned int matrix_expected = output_signals[i];
        assert((getreg(&m, IOMUX_BASE + gpio * 4U) & IOMUX_MCU_SEL_MASK) == (1U << 12));
        assert((getreg(&m, IOMUX_BASE + gpio * 4U) & ~IOMUX_MCU_SEL_MASK) == TEST_PAD_FIELDS);
        if (i < 2) matrix_expected |= TEST_MATRIX_OE_SEL;
        assert(getreg(&m, GPIO_MATRIX_OUT_BASE + gpio * 4U) == matrix_expected);
    }}
    assert(getreg(&m, GPIO_BASE + 0x44U) & (1U << 28));
    assert(getreg(&m, GPIO_BASE + 0x38U) & (1U << 9));
    assert(getreg(&m, CLK_BASE + 0x6cU) & (1U << 23));

    memset(&m, 0, sizeof(m)); m.stall = 1;
    assert(mosaico_splash_run(&io, 0xf800) != 0);
    assert(m.now <= 103 && m.ntx == 0);
    memset(&m, 0, sizeof(m)); m.stall = 2;
    assert(mosaico_splash_run(&io, 0xf800) != 0);
    assert(m.now <= 103 && m.ntx == 1);
    puts("S31 Mosaico splash MMIO sequence and bounded timeout passed");
    return 0;
}}
'''
compile_and_run(args, program, cflags=('-Wall', '-Wextra', '-Werror'))
