# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check NetBSD RISC-V bootm image discovery')
s = (args.source / 'boot/bootm.c').read_text()
m = re.search(r'(?m)^static int bootm_find_other\s*\([^;{}]*\)\s*\{', s)
assert m
i = m.end() - 1; d = 1; j = i + 1
while d:
 if s[j] == '{': d += 1
 if s[j] == '}': d -= 1
 j += 1
body = s[m.start():j]
prefix = r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long ulong;
#define IS_ENABLED(x) (x)
#define IH_TYPE_KERNEL 1
#define IH_TYPE_KERNEL_NOLOAD 2
#define IH_TYPE_MULTI 3
#define IH_OS_LINUX 1
#define IH_OS_VXWORKS 2
#define IH_OS_EFI 3
#define IH_OS_TEE 4
#define IH_OS_ELF 5
#define IH_OS_NETBSD 6
static struct { struct { int type, os; } os; int legacy_hdr_valid; } images;
static int calls;
static int bootm_find_images(ulong addr, const char *rd, const char *fdt,
 ulong start, ulong size) {
 calls++;
 if (addr != 0x50c00000 || strcmp(rd,"50000000:400000") ||
     strcmp(fdt,"conf") || start || size) abort();
 return 27;
}
'''
main = r'''
int main(void) {
 int type, os, ret, want, legacy;
 for (legacy=0;legacy<=1;legacy++) for (type=0;type<=4;type++) for(os=0;os<=6;os++) {
  images.os.type=type; images.os.os=os; images.legacy_hdr_valid=legacy; calls=0;
  ret=bootm_find_other(0x50c00000,"50000000:400000","conf");
  want=(type>=1 && type<=3 && (os>=1 && os<=5 || (CONFIG_RISCV && CONFIG_FIT && !legacy && os==6)));
  if(calls != want || ret != (want ? 27 : 0)) return 1;
 }
 puts("NetBSD/RISC-V bootm discovery and other architectures passed");
 return 0;
}
'''
for is_riscv in (0, 1):
 for fit in (0, 1):
  compile_and_run(args, '#define CONFIG_RISCV %d\n#define CONFIG_FIT %d\n' % (is_riscv, fit) + prefix + body + main)
