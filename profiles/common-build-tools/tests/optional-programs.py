#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check optional test/example controls against the selected upstream sources."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--distdir', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
cases = (
    ('math/libtommath', 'libtommath-1.3.0', 'tests', 'BUILD_TESTING', 'add_subdirectory(demo)'),
    ('graphics/libspng', 'libspng-0.7.4', 'examples', 'BUILD_EXAMPLES', 'add_executable(example'),
    ('graphics/libjpeg-turbo', 'libjpeg-turbo-3.2.1', 'tests', 'WITH_TESTS', 'add_executable(tjunittest'),
)
with tempfile.TemporaryDirectory(prefix='optional-programs-', dir=a.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for package, dist, option, cmake, evidence in cases:
        recipe = root / 'pkgsrc' / package
        archive = a.distdir / (dist + '.tar.gz')
        expected = re.search(r'^SHA512 \(' + re.escape(archive.name) + r'\) = ([0-9a-f]+)$',
                             (recipe / 'distinfo').read_text(), re.M)
        if not expected or hashlib.sha512(archive.read_bytes()).hexdigest() != expected.group(1):
            raise SystemExit('incorrect distfile: ' + package)
        with tarfile.open(archive) as tar:
            text = tar.extractfile(dist + '/CMakeLists.txt').read().decode()
        if not re.search(r'option\(\s*' + cmake + r'\b', text) or evidence not in text:
            raise SystemExit('upstream option or target missing: ' + package)
        source = (recipe / 'options.mk').read_text()
        source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                           for line in source.splitlines())
        for options, enabled in (('', False), (option, True)):
            fixture.write_text('PKG_OPTIONS=' + options + '\n' + source +
                               '\nshow:\n\t@printf "%s\\n" "${CMAKE_CONFIGURE_ARGS}"\n')
            r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                               capture_output=True, text=True, check=True)
            expected_arg = '-D' + cmake + '=' + ('ON' if enabled else 'OFF')
            if expected_arg not in r.stdout.split():
                raise SystemExit('incorrect selection for ' + package + '/' + options)
print('PASS: three upstream optional program controls, default off and opt-in on')
