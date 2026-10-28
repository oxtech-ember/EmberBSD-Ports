#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile V8 platform sources with an explicitly selected EmberBSD compiler."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for arg in ('source', 'cxx', 'libcxx', 'abseil', 'gtest-root', 'common-gtest-prod', 'nm'):
    parser.add_argument('--' + arg, required=True, type=Path)
a = parser.parse_args()
for path in (a.source, a.cxx, a.libcxx, a.abseil, a.gtest_root, a.common_gtest_prod, a.nm):
    if not path.is_absolute():
        parser.error('all selected inputs must be absolute paths')
gtest = a.gtest_root / 'third_party/googletest/src/googletest/include/gtest/gtest_prod.h'
assert gtest.read_bytes() == a.common_gtest_prod.read_bytes(), 'GTest macro header differs from common provider'
common = [str(a.cxx), '-std=c++20', '-nostdinc++', '-isystem', str(a.libcxx),
          '-I.', '-Iinclude', '-I' + str(a.abseil), '-I' + str(a.gtest_root)]
with tempfile.TemporaryDirectory(prefix='v8-target-compile-') as tmp:
    for debug in (False, True):
        objects = []
        for source in ('src/base/platform/platform-posix.cc', 'src/base/platform/platform-openbsd.cc'):
            out = Path(tmp) / (Path(source).stem + str(debug) + '.o')
            cmd = common + (['-DDEBUG=1'] if debug else []) + ['-c', source, '-o', str(out)]
            result = subprocess.run(cmd, cwd=a.source, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert result.returncode == 0, (source, debug, result.stderr)
            objects.append(out)
        missing = subprocess.run([str(a.nm), '--undefined-only', str(objects[0])],
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert missing.returncode == 0 and any(line.split()[-1:] == ['_lwp_self'] for line in missing.stdout.splitlines()), 'target thread ID does not reference _lwp_self'
        result = subprocess.run([str(a.nm), '--defined-only', '--demangle', *map(str, objects)],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, result.stderr
        for name in ('ObtainCurrentThreadStackStart', 'ObtainCurrentThreadStackReservedLimit'):
            symbol = ' T v8::base::Stack::' + name + '()'
            assert sum(line.endswith(symbol) for line in result.stdout.splitlines()) == 1, name
    for header in ('src/base/platform/memory.h', 'src/base/strings.h', 'src/common/globals.h'):
        result = subprocess.run(common + ['-fsyntax-only', '-x', 'c++', '-'], cwd=a.source,
                                input='#include "' + header + '"\n', text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, (header, result.stderr)
print('EmberBSD platform objects, stack symbols, and headers: PASS')
