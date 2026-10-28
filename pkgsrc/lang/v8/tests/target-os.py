#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check V8 target OS fallback, explicit cross target and identifiers."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--clang', type=Path, required=True)
a = p.parse_args()
t = (a.source / 'include/v8config.h').read_text()
start = t.index('#ifdef V8_HAVE_TARGET_OS')
end = t.index('// C library detection', start)
probe = t[start:end]
for host in ('OPENBSD', 'FREEBSD', 'NETBSD', 'MACOS', 'LINUX'):
    for target in (None, 'OPENBSD', 'FREEBSD', 'NETBSD', 'MACOS', 'LINUX'):
        expected = target or host
        args = [str(a.clang), '-E', '-dM', '-x', 'c++', '-DV8_OS_' + host]
        if target:
            args += ['-DV8_HAVE_TARGET_OS', '-DV8_TARGET_OS_' + target]
        r = subprocess.run(args + ['-'], input=probe, text=True, capture_output=True, check=True)
        macros = {line.split()[1]: line.split(maxsplit=2)[2] if len(line.split(maxsplit=2)) == 3 else '' for line in r.stdout.splitlines() if line.startswith('#define ')}
        selected = [x for x in ('OPENBSD', 'FREEBSD', 'NETBSD', 'MACOS', 'LINUX') if 'V8_TARGET_OS_' + x in macros]
        assert selected == [expected], (host, target, selected)
        assert ('V8_TARGET_OS_BSD' in macros) == (expected in ('OPENBSD', 'FREEBSD', 'NETBSD'))
        assert macros['V8_TARGET_OS_STRING'] == '"' + expected.lower() + '"'
print('V8 target OS: native fallback and explicit cross identifiers PASS')
