# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run

args = arguments('Check proftool alignment macro')
source = (args.source / 'tools/proftool.c').read_text()
macros = '\n'.join(line for line in source.splitlines()
                   if line.startswith('#define __ALIGN_MASK(') or line.startswith('#define PROF_ALIGN('))
assert macros.count('#define') == 2
main = '''
#include <assert.h>
int main(void) {
 assert(PROF_ALIGN(0UL, 4096) == 0);
 assert(PROF_ALIGN(1UL, 4096) == 4096);
 assert(PROF_ALIGN(4096UL, 4096) == 4096);
 assert(PROF_ALIGN(4097UL, 4096) == 8192);
 return 0;
}
'''
compile_and_run(args, macros + main)
print('proftool alignment checks passed')
