#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the libidn2 examples selector against its actual generated Makefile."""
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
p.add_argument('--gmake', type=Path, required=True)
p.add_argument('--patch', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
recipe = root/'pkgsrc/devel/libidn2'
distinfo = (recipe/'distinfo').read_text()
digest = re.search(r'^SHA512 \(' + re.escape(a.archive.name) + r'\) = ([a-f0-9]+)$', distinfo, re.M)
if not digest or hashlib.sha512(a.archive.read_bytes()).hexdigest() != digest.group(1):
    raise SystemExit('wrong libidn2 archive')
patch = recipe/'patches/patch-Makefile-examples'
expected = re.search(r'^SHA1 \(patch-Makefile-examples\) = ([a-f0-9]+)$', distinfo, re.M)
if not expected or hashlib.sha1(patch.read_bytes()).hexdigest() != expected.group(1):
    raise SystemExit('libidn2 recipe patch digest differs')
with tempfile.TemporaryDirectory(prefix='libidn2-options-', dir=a.work_parent) as work:
    w = Path(work)
    with tarfile.open(a.archive) as archive:
        for name in ('Makefile.am', 'Makefile.in'):
            (w/name).write_bytes(archive.extractfile('libidn2-2.3.8/'+name).read())
    with patch.open('rb') as inp:
        subprocess.run([str(a.patch), '-s', '-p0', '-d', str(w)], stdin=inp, check=True)
    source = (recipe/'options.mk').read_text()
    source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                       for line in source.splitlines())
    generated = (w/'Makefile.in').read_text().splitlines()
    real = [x for x in generated if x.startswith(('EXAMPLES_SUBDIR =', 'SUBDIRS ='))]
    if len(real) != 2:
        raise SystemExit('generated Makefile subdirectories changed')
    for opts, enabled in (('', False), ('examples', True)):
        f = w/'fixture.mk'
        f.write_text('PKG_OPTIONS=' + opts + '\n' + source +
                     '\nshow:\n\t@printf "%s\\n" "${MAKE_FLAGS}"\n')
        out = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(f), 'show'],
                             capture_output=True, text=True, check=True).stdout.split()
        if ('EXAMPLES_SUBDIR=' in out) == enabled:
            raise SystemExit('wrong package examples selection')
        f.write_text('\n'.join(real) + '\nam__append_1 = doc\nshow:\n\t@echo $(SUBDIRS)\n')
        cmd = [str(a.gmake), '-s', '-f', str(f), 'show']
        if not enabled:
            cmd.append('EXAMPLES_SUBDIR=')
        dirs = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()
        if ('examples' in dirs) != enabled or not {'gl', 'unistring', 'lib', 'src', 'fuzz', 'po', 'doc', 'tests'} <= set(dirs):
            raise SystemExit('libidn2 non-example subdirectories changed')
print('PASS: actual libidn2 source patch and both examples selections')
