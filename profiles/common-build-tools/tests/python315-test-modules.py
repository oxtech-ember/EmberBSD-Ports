#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check optional Python test payload against the pinned upstream install rules."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
recipe = root / 'pkgsrc/lang/python315'
digest = re.search(r'^SHA256 \(Python-3\.15\.2\.tar\.xz\) = ([a-f0-9]+)$',
                   (recipe / 'distinfo').read_text(), re.M)
if not digest or hashlib.sha256(a.archive.read_bytes()).hexdigest() != digest.group(1):
    raise SystemExit('Python archive is not the selected distfile')
with tarfile.open(a.archive) as archive:
    make = archive.extractfile('Python-3.15.2/Makefile.pre.in').read().decode()
    configure = archive.extractfile('Python-3.15.2/configure').read().decode()
section = re.search(r'(?ms)^TESTSUBDIRS=\s*(.*?)(?=^[A-Za-z_][A-Za-z_0-9]*\s*[:?+]?=)', make)
if not section or '--disable-test-modules' not in configure:
    raise SystemExit('upstream test module contract changed')
dirs = set(section.group(1).replace('\\', ' ').split())
blocks = re.split(r'checking for stdlib extension module ([^ ]+)', configure)
modules = {blocks[i].strip().removesuffix('...') for i in range(1, len(blocks)-1, 2)
           if 'TEST_MODULES' in blocks[i+1]}

def is_test(line):
    line = re.sub(r'^\$\{PLIST\.[^}]+\}', '', line)
    parts = line.split('/', 2)
    rel = parts[2] if len(parts) == 3 and parts[0] == 'lib' and parts[1].startswith('python') else ''
    directory, _, leaf = rel.rpartition('/')
    return directory in dirs or (directory == 'lib-dynload' and leaf.endswith('.so') and leaf[:-3] in modules)

normal = [x for x in (recipe / 'PLIST').read_text().splitlines() if not x.startswith('@comment')]
tests = [x for x in (recipe / 'PLIST.test-modules').read_text().splitlines() if not x.startswith('@comment')]
if not tests or any(is_test(x) for x in normal) or any(not is_test(x) for x in tests):
    raise SystemExit('Python PLIST partition differs from upstream test install contract')
if len(set(normal + tests)) != len(normal) + len(tests):
    raise SystemExit('Python PLIST partition has duplicates')
if not any('/json/' in x for x in normal) or not any('/lib-dynload/_ssl.so' in x for x in normal):
    raise SystemExit('ordinary standard library missing')
source = (recipe / 'options.mk').read_text()
source = '\n'.join('' if line.lstrip().startswith('.include ') else line for line in source.splitlines())
with tempfile.TemporaryDirectory(prefix='python-options-', dir=a.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for opts, disabled in (('', False), ('no-test-modules', True)):
        fixture.write_text('OPSYS=NetBSD\nMACHINE_PLATFORM=NetBSD-11-aarch64\n'
                           'PKGDIR=/recipe\nPLIST_SRC_DFLT=/recipe/PLIST\nPKG_OPTIONS=' + opts
                           + '\n' + source + '\nshow:\n\t@printf "%s\\n" "${CONFIGURE_ARGS}" "${PLIST_SRC}"\n')
        r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                           text=True, capture_output=True, check=True)
        args, plist = r.stdout.splitlines()
        if ('--disable-test-modules' in args) != disabled:
            raise SystemExit('incorrect Python configure selection')
        if ('/recipe/PLIST.test-modules' in plist) == disabled:
            raise SystemExit('incorrect Python PLIST selection')
print('PASS: Python upstream test-only partition and both option selections')
