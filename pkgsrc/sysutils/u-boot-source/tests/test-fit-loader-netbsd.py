# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
"""Execute real FIT loader on a supplied kernel FIT with real libfdt/SHA-256.

FIT traversal and metadata mapping collaborators below use libfdt directly;
actual U-Boot hash verification calls OpenSSL SHA-256 for the digest.
"""
import re
import sys
from pathlib import Path
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args=arguments('Exercise FIT NetBSD loader', lambda p: p.add_argument('--fit',type=Path,required=True))
fit=args.fit.resolve(strict=True)
s=(args.source/'boot/image-fit.c').read_text()
def get(name):
 m=re.search(r'(?m)^(?:static )?int\s+'+name+r'\s*\([^;{}]*\)\s*\{',s);assert m,name
 i=m.end()-1;d=1;j=i+1
 while d:
  if s[j]=='{':d+=1
  if s[j]=='}':d-=1
  j+=1
 return s[m.start():j]+'\n'
p=r'''#include <libfdt.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
typedef unsigned long ulong;
#define CONFIG_RISCV 1
#define CONFIG_SANDBOX 0
#define CONFIG_FIT_BEST_MATCH 0
#define CONFIG_FIT_IMAGE_POST_PROCESS 0
#define IS_ENABLED(x) (x)
#define CONFIG_FIT_HASH_VERIFY 1
#define CONFIG_FIT_SIGNATURE 0
#define CONFIG_IS_ENABLED(x) CONFIG_##x
#define FIT_IMAGE_ENABLE_VERIFY 0
#define IMAGE_SIZE_INVAL 0
#define IH_TYPE_KERNEL 1
#define IH_TYPE_FLATDT 2
#define IH_TYPE_FIRMWARE 3
#define IH_TYPE_TEE 4
#define IH_TYPE_TFA_BL31 5
#define IH_TYPE_KERNEL_NOLOAD 6
#define IH_TYPE_LOADABLE 7
#define IH_TYPE_RAMDISK 8
#define IH_TYPE_FPGA 9
#define CONFIG_FIT_CIPHER 0
#define IMAGE_ENABLE_DECRYPT 0
#define FIT_LOAD_OPTIONAL_NON_ZERO 2
#define fit_image_uncipher(...) 0
#define fit_get_size(f) fdt_totalsize(f)
#define FIT_ALGO_PROP "algo"
#define FIT_VALUE_PROP "value"
#define FIT_IGNORE_PROP "uboot-ignore"
#define FIT_HASH_NODENAME "hash"
#define FIT_SIG_NODENAME "signature"
#define FIT_MAX_HASH_LEN 64
#define ALLOC_CACHE_ALIGN_BUFFER(type,name,len) type name[len]
#define fit_get_debug(...) ((void)0)
#define fit_image_verify_required_sigs_quiet(...) 0
#define fit_image_check_sig_quiet(...) 0
#define IH_OS_LINUX 1
#define IH_OS_U_BOOT 2
#define IH_OS_TEE 3
#define IH_OS_OPENRTOS 4
#define IH_OS_EFI 5
#define IH_OS_VXWORKS 6
#define IH_OS_ELF 7
#define IH_OS_NETBSD 8
#define IH_COMP_NONE 0
#define IH_COMP_GZIP 1
#define FIT_LOAD_IGNORED 0
#define FIT_LOAD_REQUIRED 1
enum fit_load_op { LOAD_IGNORED=0,LOAD_REQUIRED=1 };
struct bootm_headers { int verify; const char *fit_uname_cfg; struct { uint8_t arch; } os; };
#define tools_build() 0
#define bootstage_mark(...) ((void)0)
#define bootstage_error(...) ((void)0)
#define log_debug(...) ((void)0)
#define gd_fdt_blob() NULL
#define upl_add_image(...) ((void)0)
static int image_ph_type(int t) {return t;}
static int image_ph_phase(int t) {(void)t;return 0;}
static void *map_sysmem(ulong a,ulong n) {(void)n;return (void *)(uintptr_t)a;}
static ulong map_to_sysmem(const void *p) {return (ulong)(uintptr_t)p;}
static const char *fit_get_image_type_property(int t) {return t==IH_TYPE_KERNEL?"kernel":"fdt";}
static const char *genimg_get_phase_name(int p) {(void)p;return "phase";}
static const char *genimg_get_os_name(int n) {(void)n;return "os";}
static const char *genimg_get_arch_name(int n) {(void)n;return "arch";}
static const char *genimg_get_type_name(int n) {(void)n;return "type";}
#define fit_get_name(f,n,l) fdt_get_name(f,n,l)
static int fit_check_format(const void *f,ulong n) {(void)n;return fdt_check_full(f,fdt_totalsize(f));}
static int fit_image_get_node(const void *f,const char *name) {int n=fdt_path_offset(f,"/images");return fdt_subnode_offset(f,n,name);}
static int fit_conf_find_compat(const void *f,const void *g) {(void)f;(void)g;return -ENOENT;}
static int fit_conf_get_node(const void *f,const char *name) {int n=fdt_path_offset(f,"/configurations");if(!name) name=fdt_getprop(f,n,"default",NULL);return name?fdt_subnode_offset(f,n,name):-ENOENT;}
static int fit_config_verify(const void *f,int n) {(void)f;(void)n;return 0;}
static int fit_conf_get_prop_node(const void *f,int n,const char *p,int phase) {const char *v=fdt_getprop(f,n,p,NULL);(void)phase;return v?fit_image_get_node(f,v):-ENOENT;}
static void fit_image_print(const void *f,int n,const char *p) {(void)f;(void)n;(void)p;}
static int fit_image_verify(const void *fit,int n);
static int fit_image_check_target_arch(const void *f,int n) {(void)f;(void)n;return 1;}
static int fit_image_get_arch(const void *f,int n,uint8_t *v) {const char *p=fdt_getprop(f,n,"arch",NULL);*v=7;return !p||strcmp(p,"riscv");}
static int fit_image_check_type(const void *f,int n,int t) {const char *p=fdt_getprop(f,n,"type",NULL);return p&&((t==IH_TYPE_KERNEL&&!strcmp(p,"kernel"))||(t==IH_TYPE_FLATDT&&!strcmp(p,"flat_dt"))||(t==IH_TYPE_KERNEL_NOLOAD&&!strcmp(p,"kernel_noload"))||(t==IH_TYPE_FIRMWARE&&!strcmp(p,"firmware")));}
static int fit_image_check_os(const void *f,int n,int o) {const char *p=fdt_getprop(f,n,"os",NULL);return p&&((o==IH_OS_NETBSD&&!strcmp(p,"netbsd"))||(o==IH_OS_LINUX&&!strcmp(p,"linux")));}
static int fit_image_get_os(const void *f,int n,uint8_t *v) {*v=fit_image_check_os(f,n,IH_OS_NETBSD)?IH_OS_NETBSD:0;return 0;}
static int fit_image_get_data(const void *f,int n,const void **d,size_t *z) {int l;*d=fdt_getprop(f,n,"data",&l);*z=l;return *d?0:-1;}
static int fit_image_get_load(const void *f,int n,ulong *v) {const fdt32_t *p=fdt_getprop(f,n,"load",NULL);if(!p)return -1;*v=fdt32_to_cpu(*p);return 0;}
static int fit_image_get_comp(const void *f,int n,uint8_t *v) {const char *p=fdt_getprop(f,n,"compression",NULL);*v=p&&!strcmp(p,"gzip")?IH_COMP_GZIP:IH_COMP_NONE;return 0;}
static int image_decomp(int c,ulong l,ulong d,int t,void *o,void *i,ulong z,ulong m,ulong *e) {(void)c;(void)l;(void)d;(void)t;(void)o;(void)i;(void)z;(void)m;(void)e;abort();}
static int calculate_hash(const void *data,int len,const char *name,uint8_t *out,int *outlen) {
 unsigned int n;if(strcmp(name,"sha256") || !EVP_Digest(data,len,out,&n,EVP_sha256(),NULL)) return -1;
 *outlen=n;return 0;
}
static void board_fit_image_post_process(const void *f,int n,void **p,size_t *z) {(void)f;(void)n;(void)p;(void)z;}
'''
for name in ('fit_image_hash_get_algo','fit_image_hash_get_value','fit_image_hash_get_ignore',
             'fit_image_check_hash','fit_image_verify_with_data_quiet',
             'fit_image_verify_with_data','fit_image_verify','fit_image_select','fit_image_load'):
 p+=get(name)
p+=r'''
int main(int argc,char **argv) {
 FILE *fp;long size;void *fit;struct bootm_headers images={.verify=1};ulong data,len;uint8_t arch;int node;
 if(argc!=2 || !(fp=fopen(argv[1],"rb")) || fseek(fp,0,SEEK_END) || (size=ftell(fp))<=0 || fseek(fp,0,SEEK_SET)) return 1;
 fit=malloc(size);if(!fit || fread(fit,1,size,fp)!=(size_t)size) return 2;fclose(fp);
 node=fit_image_load(&images,(ulong)(uintptr_t)fit,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len);
 #if !CONFIG_RISCV
 if(node>=0) return 12;
 free(fit);puts("NetBSD kernel rejected on other architecture");return 0;
#endif
 if(node<0 || fit_image_get_arch(fit,node,&arch) || arch!=7 || !len || !fit_image_check_os(fit,node,IH_OS_NETBSD) || !images.fit_uname_cfg || strcmp(images.fit_uname_cfg,"conf")) return 3;
 node=fit_image_load(&images,(ulong)(uintptr_t)fit,NULL,NULL,7,IH_TYPE_FLATDT,0,LOAD_IGNORED,&data,&len);
 if(node<0 || !len) return 4;
 void *dtb=malloc(len);if(!dtb) return 5;memcpy(dtb,(void *)(uintptr_t)data,len);
 if(fdt_check_full(dtb,len)) return 6;
 free(dtb);
 int kernel=fit_image_get_node(fit,"kernel");
 if(fdt_setprop_inplace(fit,kernel,"os","bogus!",7)) return 7;
 if(fit_image_load(&images,(ulong)(uintptr_t)fit,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len)>=0) return 8;
 if(fdt_setprop_inplace(fit,kernel,"os","netbsd",7)) return 9;
 int z;uint8_t *payload=(uint8_t *)fdt_getprop(fit,kernel,"data",&z);if(!payload || !z) return 10;
 payload[0]^=1;
 if(fit_image_load(&images,(ulong)(uintptr_t)fit,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len)>=0) return 11;
 payload[0]^=1;
 void *alt=malloc(size+1024);if(!alt || fdt_open_into(fit,alt,size+1024)) return 12;
 kernel=fit_image_get_node(alt,"kernel");
 if(fdt_setprop_string(alt,kernel,"type","kernel_noload")) return 13;
 if(fit_image_load(&images,(ulong)(uintptr_t)alt,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len)<0) return 14;
 kernel=fit_image_get_node(alt,"kernel");
 if(fdt_setprop_string(alt,kernel,"type","firmware")) return 17;
 if(fit_image_load(&images,(ulong)(uintptr_t)alt,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len)>=0) return 18;
 kernel=fit_image_get_node(alt,"kernel");
 if(fdt_setprop_string(alt,kernel,"type","kernel_noload")) return 19;
 kernel=fit_image_get_node(alt,"kernel");
 if(fdt_setprop_string(alt,kernel,"os","linux")) return 15;
 if(fit_image_load(&images,(ulong)(uintptr_t)alt,NULL,NULL,7,IH_TYPE_KERNEL,0,LOAD_IGNORED,&data,&len)<0) return 16;
 free(alt);free(fit);puts("real FIT loader: kernel/noload/FDT SHA accepted; wrong OS and hash rejected");return 0;
}
'''
for riscv in (0,1):
 compile_and_run(args,p.replace('#define CONFIG_RISCV 1',f'#define CONFIG_RISCV {riscv}'),include=(args.host_prefix/'include',),libraries=('fdt','crypto'),run_args=(fit,))
