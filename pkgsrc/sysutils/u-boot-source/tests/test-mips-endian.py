# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check MIPS host endian field adapters')
source = (args.source / 'tools/mips-relocs.c').read_text()
macros = source[source.index('#define hdr_field'):source.index('struct mips_reloc')]
header = r'''#include <assert.h>
#include <compiler.h>
#include <elf.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
static Elf32_Ehdr e32, *ehdr32 = &e32;
static Elf64_Ehdr e64, *ehdr64 = &e64;
static Elf32_Phdr p32, *phdr32 = &p32;
static Elf64_Phdr p64, *phdr64 = &p64;
'''
body = r'''int
main(void)
{
	for (int be = 0; be < 2; be++) {
		is_be = be;
		for (int wide = 0; wide < 2; wide++) {
			is_64 = wide;
			memset(&e32, 0, sizeof(e32));
			memset(&e64, 0, sizeof(e64));
			memset(&p32, 0, sizeof(p32));
			memset(&p64, 0, sizeof(p64));
			set_hdr_field(e, 0, e_type, 0x1234);
			unsigned char *b =
			    (unsigned char *)(wide ? (void *)&e64.e_type
						   : (void *)&e32.e_type);
			assert(b[0] == (be ? 0x12 : 0x34) &&
			       b[1] == (be ? 0x34 : 0x12));
			assert(hdr_field(e, 0, e_type) == 0x1234);
			uint64_t value = wide ? UINT64_C(0x0123456789abcdef)
					      : UINT32_C(0x12345678);
			set_hdr_field(p, 0, p_offset, value);
			b = (unsigned char *)(wide ? (void *)&p64.p_offset
						   : (void *)&p32.p_offset);
			int len = wide ? 8 : 4;
			for (int i = 0; i < len; i++)
				assert(
				    b[i] ==
				    (uint8_t)(value >>
					      (8 * (be ? (len - 1 - i) : i))));
			assert(hdr_field(p, 0, p_offset) == value);
		}
	}
	return 0;
}
'''
compile_and_run(args, header + macros + body, include=(args.host_prefix / 'include',), cflags=('-DUSE_HOSTCC', '-idirafter', str(args.source / 'include')))
print('MIPS host field endian checks passed')
