#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check libpng test build selection against the pinned Autotools source."""
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
recipe = root/'pkgsrc/graphics/png'
expected = re.search(r'^SHA512 \(' + re.escape(a.archive.name) + r'\) = ([a-f0-9]+)$',
                     (recipe/'distinfo').read_text(), re.M)
if not expected or hashlib.sha512(a.archive.read_bytes()).hexdigest() != expected.group(1):
    raise SystemExit('wrong libpng distfile')
with tarfile.open(a.archive) as archive:
    make = archive.extractfile('libpng-1.6.59/Makefile.am').read().decode()
    configure = archive.extractfile('libpng-1.6.59/configure').read().decode()
if 'all-am: $(check_PROGRAMS)' not in make or '--disable-tests' not in configure:
    raise SystemExit('libpng upstream test build contract changed')
source = (recipe/'options.mk').read_text()
source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                   for line in source.splitlines())
with tempfile.TemporaryDirectory(prefix='png-options-', dir=a.work_parent) as work:
    f = Path(work)/'fixture.mk'
    for opts, args, target in (('', '--disable-tests', ''), ('tests', '--enable-tests', 'check')):
        f.write_text('PKG_OPTIONS=' + opts + '\n' + source +
                     '\nshow:\n\t@printf "%s\\n" "${CONFIGURE_ARGS}" "${TEST_TARGET}"\n')
        r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(f), 'show'],
                           text=True, capture_output=True, check=True)
        values = r.stdout.splitlines()
        if len(values) != 2 or args not in values[0].split() or values[1] != target:
            raise SystemExit('wrong libpng test selection')
print('PASS: upstream libpng all-am test dependency and both package selections')
