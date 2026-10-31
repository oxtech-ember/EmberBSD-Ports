# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check S31 PSRAM FDT and relocation guards')
b = args.source / 'board/espressif/esp32s31'
def fn(file,marker):
 s=(b/file).read_text();a=s.index(marker);c=s.index('{',a);depth=1;i=c+1
 while depth:
  if s[i]=='{': depth+=1
  elif s[i]=='}': depth-=1
  i+=1
 return s[a:i]+'\n'
pre=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <libfdt.h>
#include "psram-layout.h"
typedef uint32_t u32; typedef uint32_t phys_addr_t; typedef uint32_t phys_size_t;
struct spl_image_info { void *fdt_addr; };
struct global_data { void *fdt_blob; uintptr_t start_addr_sp; }; static struct global_data storage, *gd=&storage;
static u32 detected; static u32 psram_size_bytes(void) { return detected; }
static void __attribute__((noreturn)) hang(void) { abort(); }
'''
s=pre+fn('spl.c','void spl_perform_board_fixups(')+fn('board.c','phys_addr_t board_get_usable_ram_top(')+fn('board.c','int arch_reserve_stacks(')
s+=r'''int main(void) {
 char blob[4096]; int node, len; fdt32_t reg[2]; const fdt32_t *got;
 struct spl_image_info image={blob}; unsigned i; u32 sizes[]={0x01000000,0x02000000,0x04000000};
 if (s31_psram_size_supported(0) || s31_psram_size_supported(0x00400000) ||
     s31_psram_size_supported(0x00800000) || s31_psram_size_supported(0x01800000)) return 1;
 if(fdt_create_empty_tree(blob,sizeof(blob))) return 2;
 node=fdt_add_subnode(blob,0,"memory@50000000"); if(node<0) return 3;
 reg[0]=cpu_to_fdt32(S31_PSRAM_BASE); reg[1]=cpu_to_fdt32(S31_PSRAM_MIN_SIZE);
 if(fdt_setprop(blob,node,"reg",reg,sizeof(reg))) return 4;
 gd->fdt_blob=blob;
 for(i=0;i<3;i++) {
  detected=sizes[i]; if(!s31_psram_size_supported(detected)) return 5;
  spl_perform_board_fixups(&image);
  if(fdt_totalsize(blob)!=sizeof(blob)) return 11;
  node=fdt_path_offset(blob,"/memory@50000000"); got=fdt_getprop(blob,node,"reg",&len);
  if(!got || len!=8 || fdt32_to_cpu(got[1])!=detected) return 6;
  if(board_get_usable_ram_top(0x30000)!=S31_PSRAM_RELOC_TOP) return 7;
 }
 gd->start_addr_sp=S31_PSRAM_RUNTIME_FLOOR+S31_PSRAM_STACK_MARGIN;
 if(arch_reserve_stacks()) return 8;
 gd->start_addr_sp--; if(arch_reserve_stacks()!=-ENOMEM) return 9;
 gd->start_addr_sp=S31_PSRAM_RELOC_TOP+1; if(arch_reserve_stacks()!=-ENOMEM) return 10;
 puts("actual SPL/proper PSRAM helpers: 16/32/64 MiB FDT updates, min-capacity and stack guards passed");
 return 0;
}
'''
compile_and_run(args, s, include=(b, args.host_prefix / 'include'), libraries=('fdt',))
