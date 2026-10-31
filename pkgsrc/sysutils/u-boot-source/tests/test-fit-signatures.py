# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import re
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check FIT signature routing and progress')
s = (args.source / 'boot/image-fit-sig.c').read_text()
def get(name):
 m = re.search(r'(?m)^(?:static )?int\s+' + name + r'\s*\([^;{}]*\)\s*\{', s)
 assert m, name
 i = m.end() - 1; d = 1; j = i + 1
 while d:
  if s[j] == '{': d += 1
  if s[j] == '}': d -= 1
  j += 1
 return s[m.start():j] + '\n'
p = r'''#include <libfdt.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define FIT_SIG_NODENAME "signature"
#define FIT_KEY_REQUIRED "required"
#define fit_get_name(f,n,l) fdt_get_name(f,n,l)
#define debug(...) ((void)0)
static char output[4096]; static size_t used;
static int log_printf(const char *fmt, ...) {
 va_list ap; int n; va_start(ap, fmt);
 n = vsnprintf(output + used, sizeof(output) - used, fmt, ap); va_end(ap);
 if (n < 0 || (size_t)n >= sizeof(output) - used) abort();
 used += n; return n;
}
static int log_puts(const char *s) { return log_printf("%s", s); }
#define printf log_printf
#define puts log_puts
/* Simulate cryptography, while executing the actual signature call graph. */
struct image_region { const void *data; size_t size; };
struct image_sign_info;
struct crypto { int (*verify)(struct image_sign_info *, struct image_region *, int, uint8_t *, int); };
struct image_sign_info { const struct crypto *crypto; bool valid; };
static int verify(struct image_sign_info *info, struct image_region *r, int n, uint8_t *v, int z) {
 (void)r; (void)n; (void)v; (void)z; return info->valid ? 0 : -1;
}
static const struct crypto crypto = { verify };
static int fit_image_setup_verify(struct image_sign_info *i, const void *f,
 int n, const void *k, int kn, char **e, bool quiet) {
 (void)k; (void)kn; (void)e; (void)quiet;
 i->crypto=&crypto; i->valid=fdt_getprop(f,n,"valid",NULL)!=NULL; return 0;
}
static int fit_image_hash_get_value(const void *f, int n, uint8_t **v, int *z) {
 static uint8_t dummy;
 (void)f; (void)n; *v=&dummy; *z=1; return 0;
}
'''
p += get('fit_image_check_sig_quiet')
p += r'''
static int fit_config_check_sig(const void *f, int n, int c, const void *k,
 int kn, char **e, bool quiet) {
 (void)c; return fit_image_check_sig_quiet(f,n,NULL,0,k,kn,e,quiet);
}
'''
for name in ('fit_image_verify_sig', 'fit_image_verify_required_sigs_quiet',
             'fit_config_verify_key', 'fit_config_verify_required_keys'):
 p += get(name)
p += r'''
#undef printf
#undef puts
int main(void) {
 char f[4096], k[4096]; int img, conf, sig, second, keys, key, all;
 bool failed;
 if (fdt_create_empty_tree(f,sizeof(f)) || fdt_create_empty_tree(k,sizeof(k))) return 1;
 img=fdt_add_subnode(f,0,"image"); if(img<0) return 2;
 if(fdt_add_subnode(f,img,"signature-ok")<0 || fdt_add_subnode(f,img,"signature-bad")<0) return 3;
 img=fdt_path_offset(f,"/image"); second=fdt_subnode_offset(f,img,"signature-ok");
 if(fdt_setprop(f,second,"valid",NULL,0)) return 4;
 conf=img;
 keys=fdt_add_subnode(k,0,"signature"); key=fdt_add_subnode(k,keys,"key");
 if(key<0 || fdt_setprop_string(k,key,"required","image")) return 5;
 keys=fdt_path_offset(k,"/signature"); key=fdt_subnode_offset(k,keys,"key");
 failed=false; used=0; output[0]=0;
 if(fit_image_verify_required_sigs_quiet(f,img,"x",1,k,&all,true,&failed) ||
    !failed || used || all) return 6;
 failed=false; used=0; output[0]=0;
 if(fit_image_verify_required_sigs_quiet(f,img,"x",1,k,&all,false,&failed) ||
    failed || !strstr(output,"- + ")) return 7;
 if(fdt_setprop_string(k,key,"required","conf")) return 8;
 failed=false; used=0; output[0]=0;
 if(fit_config_verify_required_keys(f,conf,k,true,&failed) || !failed || used) return 9;
 failed=false; used=0; output[0]=0;
 if(fit_config_verify_required_keys(f,conf,k,false,&failed) || failed ||
    !strstr(output,"- + ")) return 10;
 img=fdt_path_offset(f,"/image"); second=fdt_subnode_offset(f,img,"signature-ok");
 if(fdt_delprop(f,second,"valid")) return 11;
 failed=false; used=0; output[0]=0;
 if(!fit_config_verify_required_keys(f,conf,k,true,&failed) || !failed || !used) return 12;
 puts("FIT signature traversal: quiet/default, fallback and required failure passed");
 return 0;
}
'''
compile_and_run(args, p, include=(args.host_prefix / 'include',), libraries=('fdt',))
