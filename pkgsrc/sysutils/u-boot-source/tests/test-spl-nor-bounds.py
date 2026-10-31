# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check bounded SPL NOR reads')
s = (args.source / 'common/spl/spl_nor.c').read_text()
a = s.index('static ulong spl_nor_load_read(')
b = s.index('\nunsigned long __weak spl_nor_get_uboot_base', a)
source = r'''
#include <stdint.h>
#include <limits.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
typedef unsigned long ulong;
struct spl_load_info { int unused; };
#define debug(...) ((void)0)
static ulong region_start, region_size; static bool limited; static int copies;
static bool spl_nor_get_bounds(ulong *start, ulong *size) { *start=region_start; *size=region_size; return limited; }
static unsigned char bytes[32];
static void *map_sysmem(ulong addr, ulong count) { (void)addr; (void)count; copies++; return bytes; }
''' + s[a:b] + r'''
int main(void) {
 struct spl_load_info info; unsigned char dst[8];
 limited=true; region_start=0x1000; region_size=16;
 if (spl_nor_load_read(&info,0x1000,8,dst)!=8 || copies!=1) return 1;
 if (spl_nor_load_read(&info,0x100f,1,dst)!=1 || copies!=2) return 2;
 if (spl_nor_load_read(&info,0x0fff,1,dst) || copies!=2) return 3;
 if (spl_nor_load_read(&info,0x100f,2,dst) || copies!=2) return 4;
 if (spl_nor_load_read(&info,0x1010,1,dst) || copies!=2) return 5;
 if (spl_nor_load_read(&info,ULONG_MAX-1,4,dst) || copies!=2) return 6;
 limited=false;
 if (spl_nor_load_read(&info,ULONG_MAX-1,4,dst) || copies!=2) return 7;
 if (spl_nor_load_read(&info,ULONG_MAX,1,dst)!=1 || copies!=3) return 8;
 if (spl_nor_load_read(&info,ULONG_MAX,0,dst)!=0 || copies!=3) return 9;
 if (spl_nor_load_read(&info,0x2000,2,dst)!=2 || copies!=4) return 10;
 puts("bounded NOR: bounds, overflow, and default behavior passed"); return 0;
}
'''
compile_and_run(args, source)

# Run the real reader under the selected LLVM interpreter with actual RV32
# and RV64 unsigned-long widths; no target I/O or host libc is involved.
import os
from pathlib import Path
import subprocess
import tempfile
lli = (args.host_prefix / 'bin/lli').resolve(strict=True)
if not lli.is_relative_to(args.host_prefix):
    raise SystemExit('lli resolves outside the selected host prefix')
width_source = r'''
typedef unsigned long ulong;
typedef _Bool bool;
#define true 1
#define false 0
struct spl_load_info { int unused; };
#define debug(...) ((void)0)
static ulong region_start,region_size; static bool limited; static int copies;
static bool spl_nor_get_bounds(ulong *s,ulong *n) { *s=region_start;*n=region_size;return limited; }
static unsigned char bytes[8];
static void *map_sysmem(ulong addr,ulong count) {(void)addr;(void)count;copies++;return bytes;}
static void *memcpy(void *d,const void *s,ulong n) {(void)s;(void)n;return d;}
''' + s[a:b] + r'''
int main(void) {
 struct spl_load_info info; unsigned char dst[8]; ulong max=~0UL;
 limited=true;region_start=0x1000;region_size=16;
 if(spl_nor_load_read(&info,0x1000,8,dst)!=8 || copies!=1)return 1;
 if(spl_nor_load_read(&info,0x100f,2,dst) || copies!=1)return 2;
 if(spl_nor_load_read(&info,max-1,4,dst) || copies!=1)return 3;
 limited=false;
 if(spl_nor_load_read(&info,max,1,dst)!=1 || copies!=2)return 4;
 if(spl_nor_load_read(&info,max,0,dst) || copies!=2)return 5;
 return 0;
}
'''
env = dict(os.environ, PATH=str(args.host_prefix / 'bin') + os.pathsep +
           str(args.host_prefix / 'gnu/bin'))
with tempfile.TemporaryDirectory(prefix='spl-nor-width-') as directory:
    src=Path(directory)/'reader.c'; src.write_text(width_source)
    for bits in (32,64):
        ir=Path(directory)/f'reader{bits}.bc'
        subprocess.run([str(args.clang),f'--target=riscv{bits}-unknown-none',
                        '-ffreestanding','-fno-builtin','-O0','-emit-llvm',
                        '-c',str(src),'-o',str(ir)],check=True,env=env)
        subprocess.run([str(lli),'-force-interpreter',str(ir)],check=True,env=env)
        print(f'bounded NOR RV{bits} integer widths passed')
