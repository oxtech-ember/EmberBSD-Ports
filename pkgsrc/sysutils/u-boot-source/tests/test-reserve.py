# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check S31 U-Boot reservation sequence')
src = (args.source / 'common/board_f.c').read_text()
board = (args.source / 'board/espressif/esp32s31/board.c').read_text()
def fn(s,mark):
 a=s.index(mark);c=s.index('{',a);d=1;i=c+1
 while d:
  if s[i]=='{': d+=1
  elif s[i]=='}': d-=1
  i+=1
 return s[a:i]+'\n'
s=r'''#include "psram-layout.h"
#include <errno.h>
#include <libfdt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GD_FLG_SKIP_RELOC 1
#define SKIP_RELOCATE 0
#define SKIP_RELOCATE_CODE 0
#define CONFIG_IS_ENABLED(x) x
#define CONFIG_OF_EMBED 0
#define IS_ENABLED(x) x
#define TOTAL_MALLOC_LEN 0x1a000
#define ALIGN(x, a) (((x) + (a) - 1) & ~((a) - 1))
#define ALIGN_DOWN(x, a) ((x) & ~((a) - 1))
#define debug(...) ((void)0)
struct bd_info {
	char data[48];
};
struct board_f {
	unsigned long fdt_size;
	void *new_fdt;
};
typedef struct {
	unsigned long flags, relocaddr, mon_len, start_addr_sp;
	struct bd_info *bd;
	void *new_gd, *fdt_blob;
	struct board_f *boardf;
	char pad[256 - 4 * sizeof(unsigned long) - 4 * sizeof(void *)];
} gd_t;
_Static_assert(sizeof(gd_t) == 256,
	       "must match target GENERATED_GBL_DATA_SIZE");
static gd_t storage, *gd = &storage;
static char backing[0x90000];
static void *
map_sysmem(unsigned long a, unsigned long n)
{
	if (a < S31_PSRAM_RUNTIME_FLOOR || a + n > S31_PSRAM_RELOC_TOP)
		abort();
	return backing + (a - S31_PSRAM_RUNTIME_FLOOR);
}
'''
for marker in ('static int reserve_uboot(', 'static unsigned long reserve_stack_aligned(', 'static int reserve_malloc(', 'static int reserve_board(', 'static int reserve_global_data(', 'static int reserve_fdt('):s+=fn(src,marker)
s+=fn(board,'int arch_reserve_stacks(')+fn(src,'static int reserve_stacks(')
s+=r'''int
main(void)
{
	char blob[0x3000];
	struct board_f bf = {0};
	if (fdt_create_empty_tree(blob, sizeof(blob)))
		return 1;
	gd->fdt_blob = blob;
	gd->boardf = &bf;
	gd->relocaddr = S31_PSRAM_RELOC_TOP;
	gd->mon_len = 0x2ee40;
	if (reserve_uboot() || reserve_malloc() || reserve_board() ||
	    reserve_global_data() || reserve_fdt() || reserve_stacks())
		return 2;
	if (gd->relocaddr != 0x50fd1000 || gd->start_addr_sp != 0x50fb3ec0)
		return 3;
	printf("actual board_f reserve sequence: relocation=%#lx SP=%#lx floor "
	       "gap=%#lx\n",
	       gd->relocaddr, gd->start_addr_sp,
	       gd->start_addr_sp - S31_PSRAM_RUNTIME_FLOOR);
	return 0;
}
'''
compile_and_run(args, s, include=(args.source / 'board/espressif/esp32s31', args.host_prefix / 'include'), libraries=('fdt',))
