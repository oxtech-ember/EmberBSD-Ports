# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check ESP32-S31 flash MMU mapping')
s = (args.source / 'board/espressif/esp32s31/spl_cache_mmu.c').read_text()
a = s.index('void s31_spl_cache_mmu_init(void)')
b = s.index('\n/*', a)
source = r'''
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
static int enabled, count, disabled, restored, regcalls, flashcalls;
static u32 flashctrl;
static u32 entries[1024];
#define CONFIG_ESP32S31_NOR_MAP enabled
#define IS_ENABLED(x) (x)
#define HP_SYS_CLKRST_CACHE_CTRL0_REG 0x20587038U
#define CACHE_CTRL0_FORCE_ON_MASK 0x492U
#define SPI_MEM_C_MMU_POWER_CTRL_REG 0x20500384U
#define SPI_MEM_S_MMU_POWER_CTRL_REG 0x20502384U
#define SPI_MMU_PAGE_SIZE_M (3U << 3)
#define SPI_MMU_PAGE_SIZE_FLASH_64K (2U << 3)
#define SPI_MMU_PAGE_SIZE_PSRAM_64K 0U
#define SPI_MEM_C_CACHE_FCTRL_REG 0x2050003cU
#define SPI_MEM_C_AXI_REQ_EN 1U
#define SPI_CLOSE_AXI_INF_EN (1U << 31)
#define SOC_MMU_FLASH_INVALID 0U
#define SOC_MMU_FLASH_VALID (1U << 12)
#define SOC_MMU_ACCESS_FLASH 0U
#define S31_MMU_ENTRY_NUM 1024U
#define S31_NOR_PAGES 256U
static void reg_set_bits(u32 a,u32 b) {(void)a;(void)b;}
static void reg_write_field(u32 a,u32 b,u32 c) {
 if (a==SPI_MEM_C_CACHE_FCTRL_REG) {
  if (!disabled || restored) { flashcalls=-100; return; }
  flashctrl=(flashctrl & ~b) | (c & b); flashcalls++;
 } else regcalls++;
}
static void cache_disable_all(void) { disabled++; }
static void cache_enable_all(void) { restored++; }
static void mmu_write_flash_entry(u32 i,u32 v) { if (i<1024) entries[i]=v; count++; }
''' + s[a:b] + r'''
int main(void) {
 for (enabled=0;enabled<=1;enabled++) {
  count=disabled=restored=regcalls=flashcalls=0; flashctrl=0xc0000000U;
  s31_spl_cache_mmu_init();
  if (count!=1024 || disabled!=1 || restored!=1 || regcalls!=2) return 1;
  if (flashcalls!=enabled || flashctrl!=(enabled ? 0x40000001U : 0xc0000000U)) return 3;
  for (unsigned i=0;i<1024;i++) {
   u32 expect=enabled && i<256 ? (1U<<12)|i : 0;
   if (entries[i]!=expect) return 2;
  }
 }
 puts("flash MMU: bounded mappings and disabled profile passed"); return 0;
}
'''
compile_and_run(args, source)
