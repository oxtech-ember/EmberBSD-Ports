# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test the production compiler-rt portability header.
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--cc', required=True)
parser.add_argument('--sysroot', required=True)
parser.add_argument('--header', required=True)
parser.add_argument('--include-dir', required=True)
args = parser.parse_args()
for value in (args.cc, args.sysroot, args.header, args.include_dir):
    if not os.path.isabs(value):
        parser.error('all selected paths must be absolute')
header = Path(args.header)
if not header.is_file():
    parser.error('missing production InstrProfilingPort.h')
source = '''#include "''' + str(header) + '''"
#ifndef COMPILER_RT_ALIGNAS
#error missing COMPILER_RT_ALIGNAS
#endif
#ifndef COMPILER_RT_WEAK
#error missing COMPILER_RT_WEAK
#endif
#ifndef COMPILER_RT_VISIBILITY
#error missing COMPILER_RT_VISIBILITY
#endif
#ifndef COMPILER_RT_ALLOCA
#error missing COMPILER_RT_ALLOCA
#endif
#ifndef COMPILER_RT_ALWAYS_INLINE
#error missing COMPILER_RT_ALWAYS_INLINE
#endif
#ifndef COMPILER_RT_CLEANUP
#error missing COMPILER_RT_CLEANUP
#endif
#ifndef COMPILER_RT_USED
#error missing COMPILER_RT_USED
#endif
typedef struct COMPILER_RT_ALIGNAS(8) test_data { char x; } test_data;
_Static_assert(_Alignof(test_data) == 8, "alignment lost");
_Static_assert(sizeof(test_data) == 8, "size lost");
COMPILER_RT_WEAK COMPILER_RT_VISIBILITY COMPILER_RT_USED int test_symbol;
static COMPILER_RT_ALWAYS_INLINE int test_inline(void) { return 0; }
int probe(void) { return test_inline(); }
'''
base = [args.cc, '--target=x86_64--netbsd', '--sysroot=' + args.sysroot,
        '-std=c11', '-Werror', '-ffreestanding',
        '-DCOMPILER_RT_PROFILE_BAREMETAL=1', '-DCOMPILER_RT_HAS_ATOMICS=1',
        '-I' + args.include_dir, '-x', 'c']
for name, options in (('clang-no-gnu', ['-U__GNUC__']),
                      ('clang-native', []), ('gnu-compatible', ['-U__clang__'])):
    result = subprocess.run(base + options + ['-dM', '-E', '-'], input=source,
                            text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr)
    macros = result.stdout
    if name == 'clang-no-gnu' and ('#define __clang__ 1' not in macros or
                                    '#define __GNUC__ ' in macros):
        raise SystemExit('wrong Clang-without-GNU macro environment')
    if name == 'gnu-compatible' and ('#define __GNUC__ ' not in macros or
                                      '#define __clang__ ' in macros):
        raise SystemExit('wrong GNU-compatible macro environment')
    subprocess.run(base + options + ['-fsyntax-only', '-'], input=source,
                   text=True, check=True)
    print('PASS:', name)
