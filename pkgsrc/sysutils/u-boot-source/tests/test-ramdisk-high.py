# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Execute actual ramdisk placement in LLVM IR for RV32/RV64 type widths."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args=arguments('Check initrd_high sentinel with RISC-V ABI widths')
lli=(args.host_prefix/'bin/lli').resolve(strict=True)
if not lli.is_relative_to(args.host_prefix): raise SystemExit('lli outside host prefix')
s=(args.source/'boot/image-board.c').read_text()
m=re.search(r'(?m)^int\s+boot_ramdisk_high\s*\([^;{}]*\)\s*\{',s)
if not m: raise SystemExit('boot_ramdisk_high not found')
i=m.end()-1;d=1;j=i+1
while d:
 if s[j]=='{':d+=1
 if s[j]=='}':d-=1
 j+=1
function=s[m.start():j]
p=r'''
typedef unsigned long ulong;
typedef unsigned long long phys_addr_t;
typedef unsigned long long u64;
_Static_assert(sizeof(ulong)*8==TEST_WIDTH,"incorrect ulong width");
_Static_assert(sizeof(phys_addr_t)==8,"incorrect phys_addr_t width");
#define NULL ((void *)0)
#define bootstage_mark(...) ((void)0)
#define IS_ENABLED(x) 0
#define CONFIG_MP 0
#define ALIGN(x,y) (x)
#define ARCH_DMA_MINALIGN 64
#define CHUNKSZ 64
#define LMB_NONE 0
#define debug(...) ((void)0)
enum lmb_mem_type { LMB_MEM_ALLOC_ADDR,LMB_MEM_ALLOC_MAX,LMB_MEM_ALLOC_ANY };
static char *input; static int alloc_type,alloc_calls,copy_calls,fail_alloc;
static phys_addr_t alloc_input;static ulong copied_src,copied_dest,copied_len;
static char *env_get(const char *name) {(void)name;return input;}
static ulong hextoul(const char *s,char **end) {ulong n=0;(void)end;while (*s) {char c=*s++;unsigned v;if(c>='0'&&c<='9')v=c-'0';else if(c>='a'&&c<='f')v=c-'a'+10;else break;n=n*16+v;}return n;}
static ulong env_get_bootm_mapsize(void) {return 0x01000000UL;}
static ulong env_get_bootm_low(void) {return 0x50000000UL;}
static int lmb_alloc_mem(enum lmb_mem_type type,ulong align,phys_addr_t *addr,ulong len,int flags) {
 (void)align;(void)len;(void)flags;alloc_calls++;alloc_type=type;alloc_input=*addr;
 if(fail_alloc)return -1;if(type!=LMB_MEM_ALLOC_ADDR)*addr=0x50400000ULL;return 0;
}
static int puts(const char *s) {(void)s;return 0;}
static int printf(const char *s,...) {(void)s;return 0;}
static void memmove_wd(void *d,const void *s,ulong n,ulong chunks) {(void)chunks;copy_calls++;copied_src=(ulong)s;copied_dest=(ulong)d;copied_len=n;}
static void flush_cache(ulong a,ulong n) {(void)a;(void)n;}
'''+function+r'''
int main(void) {
 ulong start=0,end=0;
#if TEST_WIDTH == 32
 input="ffffffff";
#else
 input="ffffffffffffffff";
#endif
 char *sentinel=input;
 if(boot_ramdisk_high(0x50000000UL,0x400000UL,&start,&end) ||
    start!=0x50000000UL || end!=0x50400000UL || alloc_calls!=1 ||
    alloc_type!=LMB_MEM_ALLOC_ADDR || alloc_input!=0x50000000ULL || copy_calls) return 1;
 input="50500000";alloc_calls=copy_calls=0;
 if(boot_ramdisk_high(0x50000000UL,0x1000UL,&start,&end) ||
    alloc_type!=LMB_MEM_ALLOC_MAX || alloc_input!=0x50500000ULL ||
    start!=0x50400000UL || end!=0x50401000UL || copy_calls!=1 ||
    copied_src!=0x50000000UL || copied_dest!=0x50400000UL || copied_len!=0x1000UL) return 2;
 input="0";alloc_calls=copy_calls=0;
 if(boot_ramdisk_high(0x50000000UL,0x1000UL,&start,&end) || alloc_type!=LMB_MEM_ALLOC_ANY || copy_calls!=1) return 3;
 input=0;alloc_calls=copy_calls=0;
 if(boot_ramdisk_high(0x50000000UL,0x1000UL,&start,&end) || alloc_type!=LMB_MEM_ALLOC_MAX || alloc_input!=0x51000000ULL) return 4;
 input=sentinel;alloc_calls=copy_calls=0;fail_alloc=1;
 if(boot_ramdisk_high(0x50000000UL,0x1000UL,&start,&end)!=-1 || alloc_type!=LMB_MEM_ALLOC_ADDR || copy_calls) return 5;
 input="50500000";alloc_calls=copy_calls=0;
 if(boot_ramdisk_high(0x50000000UL,0x1000UL,&start,&end)!=-1 || alloc_type!=LMB_MEM_ALLOC_MAX || copy_calls) return 7;
 fail_alloc=0;alloc_calls=0;start=end=9;
 if(boot_ramdisk_high(0,0,&start,&end) || start || end || alloc_calls) return 6;
 return 0;
}
'''
env=dict(os.environ);env['PATH']=os.pathsep.join((str(args.host_prefix/'bin'),str(args.host_prefix/'gnu/bin')))
with tempfile.TemporaryDirectory(prefix='uboot-ramdisk-test-') as t:
 src=Path(t)/'test.c';src.write_text(p)
 for width in (32,64):
  bc=Path(t)/f'rv{width}.bc'
  subprocess.run([str(args.clang),f'--target=riscv{width}--netbsd','-ffreestanding','-fno-builtin','-nostdlib',f'-DTEST_WIDTH={width}','-O1','-emit-llvm','-c',str(src),'-o',str(bc)],env=env,check=True)
  subprocess.run([str(lli),'-force-interpreter',str(bc)],env=env,check=True)
  print(f'actual boot_ramdisk_high LLVM IR: RV{width} sentinel/relocation/decline passed')

compile_and_run(args,"#define TEST_WIDTH 64\n"+p)
print("native actual boot_ramdisk_high ASan/UBSan passed")
