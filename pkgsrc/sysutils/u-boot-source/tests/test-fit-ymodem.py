# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check FIT YMODEM routing and stream errors')
s = (args.source / 'common/spl/spl_ymodem.c').read_text()
def get(name):
 m = re.search(r'(?m)^(?:static )?(?:ulong|int)\s+' + name + r'\s*\([^;{}]*\)\s*\{', s)
 assert m, name
 i = m.end()-1; d = 1; j = i+1
 while d:
  if s[j] == '{': d += 1
  if s[j] == '}': d -= 1
  j += 1
 return s[m.start():j]+'\n'
info = re.search(r'struct ymodem_fit_info\s*\{[^}]*\};', s).group()
p = r'''#include <stdbool.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long ulong;
#define BUF_SIZE 1024
#define FDT_MAGIC 0xd00dfeed
#define xyzModem_ymodem 1
#define xyzModem_eof -4
#define CONFIG_SYS_LOAD_ADDR 0UL
#define CONFIG_SPL_LOAD_FIT_FULL 0
#define CONFIG_SPL_LOAD_FIT 1
#define IS_ENABLED(x) (x)
#define CONFIG_IS_ENABLED(x) 1
#define debug(...) ((void)0)
struct legacy_img_hdr { unsigned magic; };
struct spl_boot_device { int unused; };
struct spl_image_info { ulong load_addr; };
typedef struct { int mode; } connection_info_t;
struct spl_load_info { void *priv; bool fit_quiet, fit_signature_failed, fit_deprecated, fit_fpga_loaded;
 ulong (*read)(struct spl_load_info *, ulong, ulong, void *); };
static int reads, mode, closed, premature; static char output[4096]; static size_t used;
static int log_printf(const char *fmt, ...) {
 va_list ap; int n; if (!closed) premature++;
 va_start(ap,fmt); n=vsnprintf(output+used,sizeof(output)-used,fmt,ap); va_end(ap);
 if(n<0 || (size_t)n>=sizeof(output)-used) abort(); used+=n; return n;
}
static int log_puts(const char *s) { return log_printf("%s",s); }
#define printf log_printf
#define puts log_puts
static int xyzModem_stream_open(connection_info_t *i, int *e) { (void)i;(void)e;return 0; }
static int xyzModem_stream_read(char *b, int sz, int *e) {
 (void)sz; reads++;
 if (reads == 1) { memset(b,0,BUF_SIZE); if(mode==4) *e=-9; return BUF_SIZE; }
 if (reads == 2) { memset(b,0,8); if(mode==1) *e=-9; if(mode==3) *e=xyzModem_eof; return 8; }
 if (mode == 5 && reads == 3) { memset(b,0,8); *e=-9; return 8; }
 if (mode == 5) *e=xyzModem_eof;
 if (mode == 2) *e=-9;
 return 0;
}
static void xyzModem_stream_close(int *e) { (void)e; closed=1; }
static void xyzModem_stream_terminate(bool b, int (*get)(void)) { (void)b;(void)get; }
static int getcymodem(void) { return -1; }
static const char *xyzModem_error(int e) { (void)e;return "failure"; }
static unsigned image_get_magic(struct legacy_img_hdr *h) { (void)h;return FDT_MAGIC; }
static void spl_load_init(struct spl_load_info *l,
 ulong (*read)(struct spl_load_info *,ulong,ulong,void *), void *p, int b) {
 (void)b; l->priv=p; l->read=read; l->fit_quiet=false; l->fit_signature_failed=false; l->fit_deprecated=false; l->fit_fpga_loaded=false;
}
static int spl_parse_image_header(struct spl_image_info *s, struct spl_boot_device *b,
 struct legacy_img_hdr *h) { (void)s;(void)b;(void)h;return 0; }
static int spl_load_simple_fit(struct spl_image_info *s, struct spl_load_info *l,
 ulong o, void *p) {
 char b[8]; (void)s;(void)o;(void)p;
 if(!l->fit_quiet) abort();
 if (mode == 3 && l->read(l,BUF_SIZE,sizeof(b),b)!=sizeof(b)) abort();
 if (mode != 3) (void)l->read(l,BUF_SIZE,sizeof(b),b);
 l->fit_signature_failed=true; l->fit_deprecated=true; l->fit_fpga_loaded=true;
 return 0;
}
'''
p += info + '\n' + get('ymodem_read_fit') + get('spl_ymodem_load_image')
p += r'''
#undef printf
#undef puts
int main(void) {
 struct spl_image_info image={0}; struct spl_boot_device dev={0}; int ret;
 for(mode=0;mode<6;mode++) {
  reads=closed=premature=0; used=0; output[0]=0;
  ret=spl_ymodem_load_image(&image,&dev);
  if(!closed || premature) return 1;
  if(mode!=4 && (!strstr(output,"signature attempts failed") ||
     !strstr(output,"DEPRECATED") || !strstr(output,"FPGA image loaded"))) return 1;
  if((mode==0 || mode==3) && (ret || !strstr(output,"hashes verified"))) return 2;
  if((mode==1 || mode==2 || mode==4 || mode==5) && (ret!=-EIO || strstr(output,"hashes verified"))) return 3;
 }
 puts("YMODEM FIT routing: deferred output, EOF and stream errors passed");
 return 0;
}
'''
compile_and_run(args, p)
