#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compile the common PFFFT roundtrips with explicitly selected tools."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cc', required=True, type=Path)
p.add_argument('--source', required=True, type=Path)
p.add_argument('--cc-arg', action='append', default=[])
p.add_argument('--scalar', action='store_true')
p.add_argument('--msvc-simulation', action='store_true')
p.add_argument('--compile-only', action='store_true')
a = p.parse_args()
if not a.cc.is_absolute():
    p.error('--cc must be an absolute selected compiler')
with tempfile.TemporaryDirectory(prefix='pffft-compat-') as tmp:
    root = Path(tmp)
    source = a.source.resolve(strict=True)
    compiler = [str(a.cc), *a.cc_arg, '-O2', '-I' + str(source / 'include'),
                '-I' + str(source / 'include/pffft')]
    sources = [source / 'src/pffft.c', source / 'src/pffft_double.c',
               source / 'src/pffft_common.c']
    if a.scalar:
        compiler.append('-DPFFFT_SIMD_DISABLE=1')
    if a.msvc_simulation:
        (root / 'preinclude.h').write_text('''#include <stdlib.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <math.h>\n#include <assert.h>\n#include <stddef.h>\nvoid pffft_test_abort(void);\n#define abort pffft_test_abort\n#define _MSC_VER 1930\n''')
        (root / 'malloc.h').write_text('''#include <stddef.h>\nvoid *pffft_test_malloca(size_t);\nvoid pffft_test_freea(void *);\n#define _malloca(size) pffft_test_malloca(size)\n#define _freea(ptr) pffft_test_freea(ptr)\n''')
        (root / 'alloc.c').write_text('''#include <stdlib.h>\nint pffft_test_allocations, pffft_test_frees;\nvoid *pffft_test_malloca(size_t n) { ++pffft_test_allocations; return getenv("PFFFT_TEST_FAIL_ALLOC") ? NULL : malloc(n); }\nvoid pffft_test_freea(void *p) { ++pffft_test_frees; free(p); }\nvoid pffft_test_abort(void) { _Exit(86); }\n''')
        compiler += ['-fms-extensions', '-Wno-ignored-pragmas', '-DPFFFT_TEST_MSVC_ALLOC',
                     '-include', str(root / 'preinclude.h'), '-I' + str(root)]
        sources.append(root / 'alloc.c')
    sources.append(Path(__file__).with_name('chromium-compat.c'))
    binary = root / 'roundtrip'
    subprocess.run([*compiler, *map(str, sources), '-lm', '-o', str(binary)], check=True)
    if not a.compile_only:
        result = subprocess.run([str(binary)], check=True, text=True, capture_output=True)
        if result.stdout != 'PFFFT compatibility roundtrips PASS\n':
            raise RuntimeError('unexpected validator or roundtrip output: ' + repr(result.stdout))
        if a.msvc_simulation:
            env = {**os.environ, 'PFFFT_TEST_FAIL_ALLOC': '1', 'PFFFT_TEST_SUPPLIED_WORK': '1'}
            supplied = subprocess.run([str(binary)], env=env, check=True, text=True, capture_output=True)
            if supplied.stdout != 'PFFFT compatibility roundtrips PASS\n':
                raise RuntimeError('supplied scratch changed after allocation failure')
            del env['PFFFT_TEST_SUPPLIED_WORK']
            failed = subprocess.run([str(binary)], env=env, capture_output=True)
            if failed.returncode != 86:
                raise RuntimeError('internal scratch failure did not abort: ' + str(failed.returncode))
print('PFFFT compatibility compile' + (' PASS' if a.compile_only else ' and roundtrips PASS'))
