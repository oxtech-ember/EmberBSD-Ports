#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the DNS platform guard and compile the patched libsync source."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True, help='prepared Chromium source root')
parser.add_argument('--gn-out', type=Path, required=True, help='configured Electron GN output')
parser.add_argument('--cc', type=Path, required=True, help='configured target C compiler')
args = parser.parse_args()
source = args.source.resolve(strict=True)
out = args.gn_out.resolve(strict=True)
cc = str(args.cc.resolve(strict=True))
dns = (source / 'net/dns/dns_config_service_posix.cc').read_text()
start = dns.index('// pledge + unveil\n')
guard = dns[start:].splitlines()[1]
assert guard.startswith('#if '), 'missing DNS platform guard'
for openbsd, netbsd, expected in ((1, 0, True), (0, 1, False), (0, 0, False)):
    text = (f'#define BUILDFLAG(x) x\n#define IS_OPENBSD {openbsd}\n'
            f'#define IS_NETBSD {netbsd}\n{guard}\npledge_guard_enabled\n#endif\n')
    result = subprocess.run([cc, '-E', '-P', '-x', 'c', '-'], input=text,
                            text=True, capture_output=True, cwd=out, check=True)
    assert ('pledge_guard_enabled' in result.stdout) == expected, (openbsd, netbsd)

values = {}
for line in (out / 'obj/third_party/libsync/libsync.ninja').read_text().splitlines():
    if ' = ' in line:
        key, value = line.split(' = ', 1)
        values[key] = value
flags = []
for key in ('defines', 'include_dirs', 'cflags', 'cflags_c'):
    flags.extend(shlex.split(values[key]))
flags = [x for x in flags if x not in ('-Wno-unused-but-set-global', '-Wno-deprecated-declarations')]
original = (source / 'third_party/libsync/src/sync.c').read_text()
assert '#pragma clang diagnostic ignored "-Wunused-function"' not in original
assert original.count('__attribute__((unused))') == 6
with tempfile.TemporaryDirectory(prefix='libsync-check-') as temporary:
    temp = Path(temporary)
    for name, body, success in (('fixed', original, True),
                                ('negative', original.replace('__attribute__((unused)) ', ''), False)):
        src = temp / (name + '.c')
        src.write_text(body)
        result = subprocess.run([cc, *flags, '-Werror=unused-function', '-c', str(src),
                                 '-o', str(temp / (name + '.o'))], cwd=out,
                                text=True, capture_output=True)
        if success:
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode != 0 and result.stderr.count('[-Werror,-Wunused-function]') == 6, result.stderr
print('DNS platform guard: 3 cases; libsync target compile and six-function negative control: PASS')
