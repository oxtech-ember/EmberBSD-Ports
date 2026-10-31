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
head=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <u-boot/zlib.h>
#define __rcode
#define HEAD_CRC 2
#define EXTRA_FIELD 4
#define ORIG_NAME 8
#define COMMENT 16
#define RESERVED 0xe0
#define DEFLATED 8
static size_t peak, live;
static void *
tracked_malloc(size_t n)
{
	size_t *p = malloc(n + sizeof(size_t));
	if (!p)
		return NULL;
	*p = n;
	live += n;
	if (live > peak)
		peak = live;
	return p + 1;
}
static void
tracked_free(void *p)
{
	if (p) {
		size_t *q = (size_t *)p - 1;
		live -= *q;
		free(q);
	}
}
#define malloc tracked_malloc
#define free tracked_free
#include UBOOT_ZALLOC_SOURCE
#undef malloc
#undef free
int zunzip(void *, int, unsigned char *, unsigned long *, int, int);
'''
mid=r'''#include UBOOT_ZUTIL_HEADER
#define CONFIG_GZIP 1
#define malloc_cache_aligned malloc
int zzip(void *, unsigned long *, unsigned char *, unsigned long, int,
	 int (*)(unsigned long, unsigned long));
#ifndef CFG_GZIP_COMPRESS_DEF_SZ
#define CFG_GZIP_COMPRESS_DEF_SZ 0x200
#endif
#define ZALLOC_ALIGNMENT 16
'''
config=r'''#include <errno.h>
typedef unsigned long ulong;
typedef unsigned int uint;
typedef size_t SizeT;
#define IH_COMP_NONE 0
#define IH_COMP_GZIP 1
#define IH_COMP_BZIP2 2
#define IH_COMP_LZMA 3
#define IH_COMP_LZO 4
#define IH_COMP_LZ4 5
#define IH_COMP_ZSTD 6
#define CONFIG_BZIP2 0
#define CONFIG_LZMA 0
#define CONFIG_LZO 0
#define CONFIG_LZ4 0
#define CONFIG_ZSTD 0
#define CONFIG_IS_ENABLED(x) CONFIG_##x
#define tools_build() 0
#define print_decomp_msg(...) ((void)0)
#define memmove_wd(a, b, c, d) memmove(a, b, c)
#define CHUNKSZ 0
#define CONSERVE_MEMORY 0
#define BZ2_bzBuffToBuffDecompress(...) 0
#define lzmaBuffToBuffDecompress(...) 0
#define lzop_decompress(...) 0
#define ulz4fn(...) 0
#define zstd_decompress(...) 0
#define abuf_init_set(...) ((void)0)
struct abuf {
	int unused;
};
'''
main=r'''int
main(int argc, char **argv)
{
	FILE *f;
	long n;
	unsigned char *in, *out, *expected;
	unsigned long outlen;
	size_t rawlen;
	int ret;
	if (argc != 4)
		return 2;
	f = fopen(argv[1], "rb");
	if (!f)
		return 3;
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	rewind(f);
	in = malloc(n);
	if (fread(in, 1, n, f) != (size_t)n)
		return 4;
	fclose(f);
	f = fopen(argv[2], "rb");
	if (!f)
		return 5;
	fseek(f, 0, SEEK_END);
	rawlen = ftell(f);
	rewind(f);
	expected = malloc(rawlen);
	if (fread(expected, 1, rawlen, f) != rawlen)
		return 6;
	fclose(f);
	out = malloc(0x600000);
	outlen = n;
	{
		ulong load_end = 0;
		ret = image_decomp(IH_COMP_GZIP, 0x50600000, 0x50c00000, 2, out,
				   in, n, 0x600000, &load_end);
		if (ret || load_end != 0x50600000 + rawlen ||
		    memcmp(out, expected, rawlen) || live)
			return 13;
		printf("real image_decomp physical end %#lx\n", load_end);
	}
	ret = gunzip(out, 0x600000, in, &outlen);
	if (ret || outlen != rawlen || memcmp(out, expected, rawlen) || live)
		return 7;
	printf("gunzip input: %lu bytes, peak zlib allocations %zu bytes\n",
	       outlen, peak);
	free(in);
	f = fopen(argv[3], "rb");
	if (!f)
		return 8;
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	rewind(f);
	in = malloc(n);
	if (fread(in, 1, n, f) != (size_t)n)
		return 9;
	fclose(f);
	outlen = 0x600000;
	ret = uncompress(out, &outlen, in, n);
	if (ret || outlen != rawlen || memcmp(out, expected, rawlen) || live)
		return 10;
	printf("uncompress input: %lu bytes\n", outlen);
	free(in);
	{
		unsigned long clen = 0x600000, dlen;
		unsigned char *compressed = malloc(clen);
		ret = gzip(compressed, &clen, expected, rawlen);
		if (ret)
			return 11;
		dlen = clen;
		ret = gunzip(out, 0x600000, compressed, &dlen);
		if (ret || dlen != rawlen || memcmp(out, expected, rawlen) ||
		    live)
			return 12;
		printf(
		    "gzip/gunzip real consumer roundtrip: %lu -> %lu bytes\n",
		    (unsigned long)rawlen, clen);
		free(compressed);
	}
	free(out);
	free(expected);
	return 0;
}
'''
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
