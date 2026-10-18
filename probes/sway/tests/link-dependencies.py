#!/usr/bin/env python3
"""Check real GCC16 ELF dependency resolution and fatal symbol warnings."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--sysroot', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
assert a.cc.is_absolute() and a.cc.is_file()
assert a.sysroot.is_absolute() and a.sysroot.is_dir()
assert a.work.is_absolute() and not a.work.exists()
assert subprocess.check_output([str(a.cc), '-dumpfullversion'], text=True).strip() == '16.2.0'
a.work.mkdir(parents=True)
environment = os.environ.copy()
environment['TMPDIR'] = str(a.work)
crt = a.sysroot / 'usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0'
assert (crt / 'crtbeginS.o').is_file()
base = [str(a.cc), '--sysroot=' + str(a.sysroot), '-B' + str(crt) + '/',
        '-L' + str(a.sysroot / 'usr/pkg/gcc16/lib'),
        '-Wl,-rpath,/usr/pkg/gcc16/lib']
sources = {
    'provider': 'int old_api(void) { return 1; }\nint safe_api(void) { return 0; }\n'
                '__asm__(".section .gnu.warning.old_api\\n.string \\\"old-api-warning\\\"\\n.previous");\n',
    'consumer': 'extern int safe_api(void); int consumer(void) { return safe_api(); }\n',
    'safe': 'extern int consumer(void); int main(void) { return consumer(); }\n',
    'old': 'extern int old_api(void); int main(void) { return old_api(); }\n',
    'indirect': 'extern int consumer(void); extern int safe_api(void);\n'
                'int main(void) { return consumer() + safe_api(); }\n',
}
for name, source in sources.items():
    (a.work / (name + '.c')).write_text(source)
records = []


def run(label, arguments):
    command = base + arguments
    r = subprocess.run(command, capture_output=True, text=True,
                       env=environment, timeout=90)
    records.append(dict(label=label, command=command, status=r.returncode,
                        stdout=r.stdout, stderr=r.stderr))
    (a.work / 'receipt.json').write_text(json.dumps(records, indent=2) + '\n')
    return r


assert run('provider', ['-shared', '-fPIC', str(a.work / 'provider.c'),
    '-Wl,-soname,libprovider.so', '-o', str(a.work / 'libprovider.so')]).returncode == 0
assert run('consumer', ['-shared', '-fPIC', str(a.work / 'consumer.c'),
    '-L' + str(a.work), '-lprovider', '-Wl,-soname,libconsumer.so',
    '-o', str(a.work / 'libconsumer.so')]).returncode == 0
for mode in ('copy', 'no-copy'):
    for kind in ('safe', 'old', 'indirect'):
        r = run(kind + '-' + mode, [str(a.work / (kind + '.c')),
            '-L' + str(a.work), '-Wl,-rpath-link,' + str(a.work),
            '-Wl,--' + mode + '-dt-needed-entries', '-Wl,--fatal-warnings',
            '-Wl,--as-needed', '-l' + ('provider' if kind == 'old' else 'consumer'),
            '-o', str(a.work / (kind + '-' + mode))])
        if kind == 'old' or (kind == 'safe' and mode == 'copy'):
            assert r.returncode != 0 and 'old-api-warning' in r.stderr, records[-1]
        elif kind == 'indirect' and mode == 'no-copy':
            assert r.returncode != 0 and 'safe_api' in r.stderr, records[-1]
        else:
            assert r.returncode == 0 and not r.stderr, records[-1]
print('PASS: direct dependencies avoid a false warning, retain fatal real warnings, and reject undeclared dependencies')
