#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Compile the V8 FreeBSD kinfo address conversion with integer fields."""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/base/platform/platform-freebsd.cc').read_text()
match = re.search(r'(#if defined\(__i386__\) \|\| defined\(V8_OS_FREEBSD\).*?#endif)', text, re.S)
assert match, 'missing FreeBSD integer address conversion'
code = ('#include <cstdint>\nstruct Record { uint64_t kve_start; uint64_t kve_end; };\n'
        'struct Range { Range(const char*, uintptr_t, uintptr_t); };\n'
        'void f(Record* map) { const char* lib_name=""; Range r(\n'
        + match.group(1).replace(')));', '));') + '\n}\n')
result = subprocess.run([str(a.clang), '-std=c++20', '-fsyntax-only',
                         '-DV8_OS_FREEBSD', '-x', 'c++', '-'], input=code, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert result.returncode == 0, result.stderr
print('FreeBSD integer address conversion syntax OK')
