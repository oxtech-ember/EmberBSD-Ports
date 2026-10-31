# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
import re
from common import arguments, compile_and_run
args = arguments('Check SPL string helpers')
s = (args.source / 'lib/string.c').read_text()
def get(n):
 m=re.search(r'(?m)^(?:__rcode\s+)?__used\s+void\s*\*\s*'+n+r'\s*\([^;{}]*\)\s*\{',s);assert m,n
 i=m.end()-1;d=1;j=i+1
 while d:
  if s[j]=='{':d+=1
  if s[j]=='}':d-=1
  j+=1
 return s[m.start():j].replace(n+'(', 'ub_'+n+'(',1)+'\n'
p=r'''#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define __rcode
#define CONFIG_IS_ENABLED(x) 1
typedef unsigned long ulong;
'''
for n in ('memset','memcpy','memmove'):p+=get(n)
p+=r'''
int
main(void)
{
	unsigned char a[320], b[320], src[320];
	for (int i = 0; i < 320; i++)
		src[i] = (unsigned char)(i * 37 + 5);
	for (int off = 0; off < 8; off++)
		for (int len = 0; len <= 128; len++) {
			memset(a, 0x5a, sizeof a);
			memset(b, 0x5a, sizeof b);
			assert(ub_memset(a + off, 0x1c3, len) == a + off);
			memset(b + off, 0x1c3, len);
			assert(!memcmp(a, b, sizeof a));
			memset(a, 0x5a, sizeof a);
			memset(b, 0x5a, sizeof b);
			assert(ub_memcpy(a + off, src + 7 - off, len) ==
			       a + off);
			memcpy(b + off, src + 7 - off, len);
			assert(!memcmp(a, b, sizeof a));
			for (int d = -7; d <= 7; d++) {
				memcpy(a, src, sizeof a);
				memcpy(b, src, sizeof b);
				assert(ub_memmove(a + 40 + off + d,
						  a + 40 + off,
						  len) == a + 40 + off + d);
				memmove(b + 40 + off + d, b + 40 + off, len);
				assert(!memcmp(a, b, sizeof a));
			}
		}
	return 0;
}
'''
compile_and_run(args, p, cflags=('-fno-builtin', '-fno-strict-aliasing'))
print('SPL string helper checks passed')
