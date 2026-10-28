#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check that BSD V8 thread IDs use their native integral interfaces."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--clang', type=Path, required=True)
a = parser.parse_args()
text = (a.source / 'src/base/platform/platform-posix.cc').read_text()
match = re.search(r'(int OS::GetCurrentThreadIdInternal\(\) \{.*?\n\})', text, re.S)
assert match
prefix = '''
int _lwp_self() { return 73; }
int pthread_getthreadid_np() { return 87; }
struct OS { static int GetCurrentThreadIdInternal(); };
'''
with tempfile.TemporaryDirectory(prefix='v8-thread-id-') as d:
    for platform, expected in (('NETBSD', 73), ('FREEBSD', 87)):
        output = Path(d) / platform
        code = prefix + match.group(1) + '\nint main() { return OS::GetCurrentThreadIdInternal() != ' + str(expected) + '; }\n'
        r = subprocess.run([str(a.clang), '-std=c++20', '-DV8_OS_' + platform,
                            '-x', 'c++', '-', '-o', str(output)], input=code,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert r.returncode == 0, r.stderr
        assert subprocess.run([str(output)]).returncode == 0
assert re.search(r'#if defined\(__NetBSD__\)\s*\n#include <lwp.h>', text)
print('NetBSD/FreeBSD native integral thread ID selection: PASS')
