# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check NetBSD RISC-V FDT/initrd discovery flow')
s = (args.source / 'boot/bootm.c').read_text()
def get(name):
 m=re.search(r'(?m)^(?:static )?int\s+'+name+r'\s*\([^;{}]*\)\s*\{',s);assert m
 i=m.end()-1; d=1; j=i+1
 while d:
  if s[j]=='{':d+=1
  if s[j]=='}':d-=1
  j+=1
 return s[m.start():j]+'\n'
p=r'''#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long ulong;
#define CONFIG_RISCV 1
#define CONFIG_FIT 1
#define CONFIG_ANDROID_BOOT_IMAGE 0
#define CONFIG_OF_LIBFDT 1
#define CONFIG_CMD_FDT 0
#define CONFIG_FPGA 0
#define IS_ENABLED(x) (x)
#define CONFIG_IS_ENABLED(x) CONFIG_##x
#define IH_TYPE_KERNEL 1
#define IH_TYPE_KERNEL_NOLOAD 2
#define IH_TYPE_MULTI 3
#define IH_OS_LINUX 1
#define IH_OS_VXWORKS 2
#define IH_OS_EFI 3
#define IH_OS_TEE 4
#define IH_OS_ELF 5
#define IH_OS_NETBSD 6
#define IH_INITRD_ARCH 7
#define IH_ARCH_DEFAULT 7
#define IMAGE_FORMAT_ANDROID 8
static struct bootm_headers { struct { int type, os; ulong start; } os;
 int legacy_hdr_valid; ulong rd_start,rd_end; void *ft_addr; ulong ft_len; } images;
static int got_rd,got_fdt, got_loadables,fail_rd,fail_fdt;
static void *map_sysmem(ulong a,int n) { (void)n;return (void *)(uintptr_t)a; }
static ulong map_to_sysmem(void *p) { return (ulong)(uintptr_t)p; }
static int genimg_get_format(void *p) { (void)p;return 0; }
static const char *simple_xtoa(ulong a) { (void)a;return "0"; }
static int boot_get_ramdisk(const char *s,struct bootm_headers *h,int a,ulong *start,ulong *end) {
 (void)h;(void)a;got_rd++;if(!s || strcmp(s,"50000000:400000")) abort();
 *start=0x50000000;*end=0x50400000;return fail_rd;
}
static int boot_get_fdt(void *p,const char *s,int a,struct bootm_headers *h,void **out,ulong *len) {
 (void)a;(void)h;got_fdt++;if((ulong)(uintptr_t)p!=0x50c00000 || s) abort();
 *out=(void *)(uintptr_t)0x50c01000;*len=0x1000;return fail_fdt;
}
static int check_overlap(const char *n,ulong a,ulong b,ulong c,ulong d) { (void)n;(void)a;(void)b;(void)c;(void)d;return 0; }
static void set_working_fdt_addr(ulong a) { (void)a; }
static int boot_get_fpga(struct bootm_headers *h) { (void)h;return 0; }
static int boot_get_loadable(struct bootm_headers *h) { (void)h;got_loadables++;return 0; }
'''
p+=get('bootm_find_images')+get('bootm_find_other')
p+=r'''
int main(void) {
 images.os.type=IH_TYPE_KERNEL;images.os.os=IH_OS_NETBSD;
 if(bootm_find_other(0x50c00000,"50000000:400000",NULL) || got_rd!=1 || got_fdt!=1 || got_loadables!=1 ||
    images.rd_start!=0x50000000 || images.rd_end!=0x50400000 || !images.ft_addr) return 1;
 got_rd=got_fdt=got_loadables=0;fail_rd=1;
 if(!bootm_find_other(0x50c00000,"50000000:400000",NULL) || got_fdt || got_loadables) return 2;
 got_rd=got_fdt=got_loadables=0;fail_rd=0;fail_fdt=1;
 if(!bootm_find_other(0x50c00000,"50000000:400000",NULL) || got_rd!=1 || got_fdt!=1 || got_loadables) return 3;
 puts("NetBSD FIT flow: initrd and FDT requested, errors propagated");return 0;
}
'''
compile_and_run(args,p)
