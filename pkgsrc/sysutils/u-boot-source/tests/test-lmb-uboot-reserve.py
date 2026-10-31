# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check U-Boot relocation reservation across DRAM banks')
s = (args.source / 'lib/lmb.c').read_text()
a = s.index('static void lmb_reserve_uboot_region(void)')
b = s.index('\nstatic void lmb_reserve_common(', a)
source = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint32_t ulong;
typedef uint64_t phys_addr_t;
#define CFG_PRAM 0
#define debug(...) ((void)0)
#define min_t(type,a,b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
static uint32_t stack_size;
#define CONFIG_STACK_SIZE stack_size
#define CONFIG_PRAM 0
#define IS_ENABLED(x) (x)
#define CONFIG_NR_DRAM_BANKS 2
#define GD_FLG_SKIP_RELOC 1
#define LMB_NOOVERWRITE 1
struct bank { uint64_t start, size; };
struct data { uint32_t start_addr_sp, initial_relocaddr, flags, mon_len; struct bank dram[2]; };
static struct data data, *gd = &data;
static char _start[1];
static uint64_t got_start, got_size; static int calls; static unsigned long pram_value;
static unsigned long env_get_ulong(const char *s,int b,unsigned long d) { (void)s;(void)b;(void)d;return pram_value; }
static int lmb_reserve(uint64_t p,uint64_t n,int flags) { (void)flags; got_start=p;got_size=n;calls++;return 0; }
''' + s[a:b] + r'''
int main(void) {
 gd->dram[0]=(struct bank){0x2f030000,0x4afb0};
 gd->dram[1]=(struct bank){0x50000000,0x1000000};
 gd->start_addr_sp=0x50fb3ec0; gd->initial_relocaddr=0x51000000;
 stack_size=0x1000000; lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50000000 || got_size!=0x1000000) { puts("cross-bank stack must clamp and reserve"); return 1; }
 calls=0; stack_size=0x20000; lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50f93ec0 || got_size!=0x6c140) { puts("stack budget reserve mismatch"); return 2; }
 calls=0; gd->start_addr_sp=0x1000; gd->initial_relocaddr=0x10000;
 gd->dram[0]=(struct bank){0,0x10000}; gd->dram[1].size=0;
 lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0 || got_size!=0x10000) { puts("32-bit stack underflow not clamped"); return 3; }
 calls=0; gd->dram[0]=(struct bank){0x50000000,0x1000000}; gd->start_addr_sp=0x50fb3ec0; gd->initial_relocaddr=0x51000000; stack_size=0x20000; pram_value=32;
 lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50f93ec0 || got_size!=0x64140) { puts("PRAM valid size changed"); return 4; }
 calls=0; pram_value=1024; lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50f93ec0 || got_size!=0x6c140) { puts("oversize PRAM must not wrap"); return 5; }
 calls=0; gd->initial_relocaddr=0x52000000; pram_value=32; lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50f93ec0 || got_size!=0x6c140) { puts("PRAM in another bank must not shrink reservation"); return 7; }
 calls=0; gd->flags=0; pram_value=0; gd->start_addr_sp=0x51000000; gd->initial_relocaddr=0x51000000;
 gd->dram[0]=(struct bank){0x51000000,0x1000000}; gd->dram[1]=(struct bank){0x50000000,0x1000000};
 lmb_reserve_uboot_region();
 if(calls!=1 || got_start!=0x50fe0000 || got_size!=0x20000) { puts("bank boundary must select stack below SP"); return 8; }
 calls=0; gd->dram[0]=(struct bank){0x50000000,0x1000000}; gd->dram[1].size=0; gd->start_addr_sp=0x50fb3ec0;
 gd->initial_relocaddr=0x51000000; pram_value=0; gd->flags=GD_FLG_SKIP_RELOC; gd->mon_len=16; lmb_reserve_uboot_region();
 if(calls!=2 || got_size!=16) { puts("skip-reloc image was not reserved"); return 6; }
 puts("U-Boot reservations: bank crossing, normal, underflow, PRAM and skip-reloc protected"); return 0;
}
'''
compile_and_run(args, source)
