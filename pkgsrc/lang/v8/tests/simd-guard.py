#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check the actual V8 SVE feature guard for BSD and other host targets."""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/objects/simd.cc').read_text()
match = re.search(r'(#if defined\(NEON64\) && defined\(__clang__\) && \\\n.*?\n#define V8_ENABLE_SIMD_SVE 1)\n', text, re.S)
assert match, 'missing V8 SVE guard'
probe = (match.group(1) + '\n#endif\n#ifdef V8_ENABLE_SIMD_SVE\n'
         'SVE_ENABLED\n#else\nNEON_ONLY\n#endif\n')
for platform, expected in (('OPENBSD', 'NEON_ONLY'), ('NETBSD', 'SVE_ENABLED'),
                           ('MACOS', 'SVE_ENABLED')):
    result = subprocess.run([str(a.clang), '-E', '-P', '-x', 'c++', '-DNEON64',
                             '-DV8_TARGET_OS_' + platform, '-'], input=probe,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0 and result.stdout.strip() == expected, (platform, result.stderr)
print('V8 SVE guard: OpenBSD fallback, NetBSD/macOS retained')
