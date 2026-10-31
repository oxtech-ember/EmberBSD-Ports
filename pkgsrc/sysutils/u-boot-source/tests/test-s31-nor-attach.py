# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check S31 flash attach ordering in RAM probe')
s = (args.source / 'board/espressif/esp32s31/spl.c').read_text()
a = s.index('void spl_board_init(void)')
b = s.index('\nu32 spl_boot_device(', a)
source = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t u32;
#define IS_ENABLED(x) (x)
static int stage, count;
static void esp_rom_spiflash_attach(u32 config, bool legacy) {
 if (stage || config || legacy) abort(); stage=1;
}
static void s31_spl_cache_mmu_init(void) { if(stage!=(CONFIG_ESP32S31_NOR_MAP ? 1 : 0))abort(); stage=2; }
static void s31_spl_pma_psram_rwx(void) { if(stage!=2)abort(); stage=3; }
static int psram_init(void) { if(stage!=3)abort(); stage=4; return 0; }
static u32 psram_size_bytes(void) { return 0x1000000; }
static bool s31_psram_size_supported(u32 n) { return n==0x1000000; }
static void hang(void) { abort(); }
static void s31_spl_cpu_switch_to_cpll(void) { if(stage!=4)abort(); }
static void s31_spl_systimer_clk_init(void) { if(stage!=4)abort(); stage=5; }
static u32 crc32(u32 seed, const unsigned char *p, unsigned size) {
 uintptr_t want=count ? 0x40020000 : 0x40002000;
 if(stage!=5 || seed || (uintptr_t)p!=want || size!=4096)abort(); count++; return 0;
}
''' + s[a:b] + r'''
int main(void) { spl_board_init(); if(stage!=5 || count!=(CONFIG_ESP32S31_NOR_PROBE ? 2 : 0))return 1; puts("ROM attach before cache and PSRAM, two NOR probe ranges: passed"); return 0; }
'''
for mapped, probe, boot in ((0, 0, 0), (1, 1, 0), (1, 0, 1)):
    compile_and_run(args, source, cflags=(f'-DCONFIG_ESP32S31_NOR_MAP={mapped}',
                    f'-DCONFIG_ESP32S31_NOR_PROBE={probe}',
                    f'-DCONFIG_ESP32S31_NOR_BOOT={boot}'))
