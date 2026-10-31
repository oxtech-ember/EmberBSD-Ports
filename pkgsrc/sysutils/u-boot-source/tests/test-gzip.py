# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
import json, os, re, subprocess, tempfile
from pathlib import Path
from common import arguments

def options(parser):
 parser.add_argument('--raw', type=Path, required=True)
 parser.add_argument('--gzip', type=Path, required=True)
 parser.add_argument('--zlib', type=Path, required=True)
args=arguments('Check actual U-Boot gzip and common zlib paths', options)

def function(path, name):
 text=(args.source/path).read_text()
 m=re.search(r'(?m)^(?:__rcode\s+)?(?:static\s+)?(?:int\s+|void\s*\*\s*|void\s+)'+name+r'\s*\([^;{}]*\)\s*\{',text)
 if not m: raise RuntimeError('missing function '+name+' in '+str(path))
 i=m.end()-1; depth=1; j=i+1
 while depth:
  if text[j]=='{':depth+=1
  elif text[j]=='}':depth-=1
  j+=1
 return text[m.start():j]+'\n'
head='#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <u-boot/zlib.h>\n#define __rcode\n#define HEAD_CRC 2\n#define EXTRA_FIELD 4\n#define ORIG_NAME 8\n#define COMMENT 16\n#define RESERVED 0xe0\n#define DEFLATED 8\nstatic size_t peak, live;\nstatic void *tracked_malloc(size_t n) { size_t *p=malloc(n+sizeof(size_t)); if (!p) return NULL; *p=n; live+=n; if(live>peak)peak=live; return p+1; }\nstatic void tracked_free(void *p) { if(p) { size_t *q=(size_t *)p-1;live-=*q;free(q); } }\n#define malloc tracked_malloc\n#define free tracked_free\n#include UBOOT_ZALLOC_SOURCE\n#undef malloc\n#undef free\nint zunzip(void *, int, unsigned char *, unsigned long *, int, int);\n'
mid='#include UBOOT_ZUTIL_HEADER\n#define CONFIG_GZIP 1\n#define malloc_cache_aligned malloc\nint zzip(void *, unsigned long *, unsigned char *, unsigned long, int, int (*)(unsigned long, unsigned long));\n#ifndef CFG_GZIP_COMPRESS_DEF_SZ\n#define CFG_GZIP_COMPRESS_DEF_SZ\t0x200\n#endif\n#define ZALLOC_ALIGNMENT\t\t16\n\n'
config='#include <errno.h>\ntypedef unsigned long ulong;typedef unsigned int uint;typedef size_t SizeT;\n#define IH_COMP_NONE 0\n#define IH_COMP_GZIP 1\n#define IH_COMP_BZIP2 2\n#define IH_COMP_LZMA 3\n#define IH_COMP_LZO 4\n#define IH_COMP_LZ4 5\n#define IH_COMP_ZSTD 6\n#define CONFIG_BZIP2 0\n#define CONFIG_LZMA 0\n#define CONFIG_LZO 0\n#define CONFIG_LZ4 0\n#define CONFIG_ZSTD 0\n#define CONFIG_IS_ENABLED(x) CONFIG_ ## x\n#define tools_build() 0\n#define print_decomp_msg(...) ((void)0)\n#define memmove_wd(a,b,c,d) memmove(a,b,c)\n#define CHUNKSZ 0\n#define CONSERVE_MEMORY 0\n#define BZ2_bzBuffToBuffDecompress(...) 0\n#define lzmaBuffToBuffDecompress(...) 0\n#define lzop_decompress(...) 0\n#define ulz4fn(...) 0\n#define zstd_decompress(...) 0\n#define abuf_init_set(...) ((void)0)\nstruct abuf { int unused; };\n'
main='int main(int argc,char **argv) {\n FILE *f; long n; unsigned char *in,*out,*expected; unsigned long outlen; size_t rawlen; int ret;\n if(argc!=4)return 2; f=fopen(argv[1],"rb");if(!f)return 3;fseek(f,0,SEEK_END);n=ftell(f);rewind(f);in=malloc(n);if(fread(in,1,n,f)!=(size_t)n)return 4;fclose(f);\n f=fopen(argv[2],"rb");if(!f)return 5;fseek(f,0,SEEK_END);rawlen=ftell(f);rewind(f);expected=malloc(rawlen);if(fread(expected,1,rawlen,f)!=rawlen)return 6;fclose(f);out=malloc(0x600000);outlen=n;\n {ulong load_end=0;ret=image_decomp(IH_COMP_GZIP,0x50600000,0x50c00000,2,out,in,n,0x600000,&load_end);if(ret||load_end!=0x50600000+rawlen||memcmp(out,expected,rawlen)||live)return 13;printf("real image_decomp physical end %#lx\\n",load_end);}\n ret=gunzip(out,0x600000,in,&outlen);if(ret||outlen!=rawlen||memcmp(out,expected,rawlen)||live)return 7;printf("gunzip input: %lu bytes, peak zlib allocations %zu bytes\\n",outlen,peak);free(in);\n f=fopen(argv[3],"rb");if(!f)return 8;fseek(f,0,SEEK_END);n=ftell(f);rewind(f);in=malloc(n);if(fread(in,1,n,f)!=(size_t)n)return 9;fclose(f);outlen=0x600000;ret=uncompress(out,&outlen,in,n);if(ret||outlen!=rawlen||memcmp(out,expected,rawlen)||live)return 10;printf("uncompress input: %lu bytes\\n",outlen);free(in);\n { unsigned long clen=0x600000, dlen; unsigned char *compressed=malloc(clen); ret=gzip(compressed,&clen,expected,rawlen); if(ret)return 11;dlen=clen;ret=gunzip(out,0x600000,compressed,&dlen);if(ret||dlen!=rawlen||memcmp(out,expected,rawlen)||live)return 12;printf("gzip/gunzip real consumer roundtrip: %lu -> %lu bytes\\n",(unsigned long)rawlen,clen);free(compressed); }\n free(out);free(expected);return 0; }\n'
head=head.replace('UBOOT_ZALLOC_SOURCE',json.dumps(str(args.source/'lib/zlib/uboot-zalloc.c')))
mid=mid.replace('UBOOT_ZUTIL_HEADER',json.dumps(str(args.source/'lib/zlib/zutil.h')))
text=head+''.join(function('lib/gunzip.c',n) for n in ('gzip_parse_header','gunzip','zunzip'))+mid+''.join(function('lib/gzip.c',n) for n in ('zalloc','zfree','gzip','zzip'))+config+function('boot/image.c','image_decomp')+main
env=dict(os.environ);env['PATH']=os.pathsep.join((str(args.host_prefix/'bin'),str(args.host_prefix/'gnu/bin')))
with tempfile.TemporaryDirectory(prefix='uboot-gzip-test-') as d:
 work=Path(d);(work/'test.c').write_text(text);(work/'malloc.h').write_text('#include <stdlib.h>\n')
 flags=[str(args.clang),'-O1','-g','-fsanitize=address,undefined', '-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-strict-aliasing','-DZ_SOLO','-Dcrc32=uboot_zlib_crc32',f'-I{work}',f"-I{args.host_prefix / 'include'}",'-idirafter',str(args.source/'include'),f"-I{args.source / 'lib/zlib'}"]
 objects=[]
 for n in ('adler32','crc32','inffast','inflate','inftrees','zutil','deflate','trees','uncompr'):
  obj=work/(n+'.o');cmd=flags.copy()
  if n=='uncompr':cmd+=['-include',str(args.source/'lib/zlib/uboot-uncompr.h')]
  cmd+=['-c',str(args.source/'lib/zlib'/(n+'.c')),'-o',str(obj)];subprocess.run(cmd,check=True,env=env);objects.append(str(obj))
 exe=work/'test';subprocess.run(flags+['-fuse-ld=lld',str(work/'test.c'),*objects,'-o',str(exe)],check=True,env=env)
 subprocess.run([str(exe),str(args.gzip),str(args.raw),str(args.zlib)],check=True,env=env)
