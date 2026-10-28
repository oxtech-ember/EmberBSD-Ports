#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check platform selection of V8's allocation-size feature."""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/base/platform/memory.h').read_text()
match = re.search(r'(#if \(V8_OS_POSIX.*?\n#define V8_HAS_MALLOC_USABLE_SIZE 1\n#endif)', text, re.S)
assert match, 'missing V8 malloc feature guard'
assert re.search(r'#elif V8_OS_FREEBSD\s*\n#include <malloc_np.h>', text), 'wrong FreeBSD header'
probe = match.group(1) + '\n#ifdef V8_HAS_MALLOC_USABLE_SIZE\nAVAILABLE\n#else\nFALLBACK\n#endif\n'
for platform, expected in (('DARWIN', 'AVAILABLE'), ('FREEBSD', 'AVAILABLE'),
                           ('NETBSD', 'FALLBACK'), ('OPENBSD', 'FALLBACK'),
                           ('LINUX', 'AVAILABLE')):
    cmd = [str(a.clang), '-E', '-P', '-x', 'c++', '-DV8_OS_POSIX=1',
           '-DV8_OS_' + platform + '=1', '-']
    result = subprocess.run(cmd, input=probe, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0 and result.stdout.strip() == expected, (platform, result.stderr)
print('V8 allocation feature: Darwin, FreeBSD, Linux; NetBSD/OpenBSD fallback')
