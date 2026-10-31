# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check FIT FPGA diagnostic routing')
s = (args.source / 'common/spl/spl_fit.c').read_text()
def get(name):
 m = re.search(r'(?m)^static\s+(?:void|int)\s+' + name + r'\s*\([^;{}]*\)\s*\{', s)
 assert m, name
 i = m.end() - 1; d = 1; j = i + 1
 while d:
  if s[j] == '{': d += 1
  if s[j] == '}': d -= 1
  j += 1
 return s[m.start():j] + '\n'
p = r'''#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct spl_fit_info { void *fit; };
struct spl_image_info { unsigned long load_addr; unsigned long size; };
struct spl_load_info { bool fit_quiet, fit_deprecated, fit_fpga_loaded; };
#define debug(...) ((void)0)
#define CONFIG_IS_ENABLED(x) 0
#define BIT_FULL 0
static char output[4096]; static size_t used;
static int log_printf(const char *fmt, ...) {
 va_list ap; int n; va_start(ap,fmt);
 n=vsnprintf(output+used,sizeof(output)-used,fmt,ap); va_end(ap);
 if(n<0 || (size_t)n>=sizeof(output)-used) abort(); used+=n; return n;
}
static int log_puts(const char *s) { return log_printf("%s",s); }
#define printf log_printf
#define puts log_puts
static const char *fdt_getprop(const void *f, int n, const char *s, int *l) {
 (void)f;(void)n;(void)s;(void)l; return NULL;
}
static int fpga_compatible2flag(int n, const char *s) { (void)n;(void)s;return 0; }
static int fpga_load(int n, const void *p, unsigned long z, int t, int f) {
 (void)n;(void)p;(void)z;(void)t;(void)f;return 0;
}
'''
p += get('warn_deprecated') + get('spl_fit_upload_fpga')
p += r'''
#undef printf
#undef puts
int main(void) {
 struct spl_fit_info ctx={0}; struct spl_image_info img={0};
 struct spl_load_info load={0};
 if(spl_fit_upload_fpga(&ctx,0,&img,&load) ||
    !strstr(output,"DEPRECATED") || !strstr(output,"FPGA image loaded")) return 1;
 used=0; output[0]=0; load.fit_quiet=true;
 if(spl_fit_upload_fpga(&ctx,0,&img,&load) || used ||
    !load.fit_deprecated || !load.fit_fpga_loaded) return 2;
 puts("FIT FPGA diagnostics: normal output and deferred flags passed");
 return 0;
}
'''
compile_and_run(args, p)
