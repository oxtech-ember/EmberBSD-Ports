#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify Qt dependency test selectors and the graphite test-tool guard."""
import argparse
from pathlib import Path
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--distdir', type=Path, required=True)
p.add_argument('--upstream', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work-parent', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
cases = (
    ('fonts/fontconfig/options.mk', 'MESON_ARGS', '-Dtests=enabled', '-Dtests=disabled'),
    ('www/libproxy/options.mk', 'MESON_ARGS', '-Dtests=true', '-Dtests=false'),
    ('devel/glib2-introspection/options.mk', 'MESON_ARGS', '-Dtests=true', '-Dtests=false'),
)
with tempfile.TemporaryDirectory(prefix='qt-test-options-', dir=a.work_parent) as work:
    w = Path(work)
    fixtures = []
    for name, var, on, off in cases:
        fixtures.append(((root/'pkgsrc'/name).read_text(), var, on, off))
    export = w/'graphics/graphite2'
    export.mkdir(parents=True)
    upstream = a.upstream/'graphics/graphite2'
    for name in ('Makefile', 'PLIST'):
        (export/name).write_bytes((upstream/name).read_bytes())
    with (root/'profiles/common-build-tools/patches/graphite2-tests-option.patch').open('rb') as patch:
        subprocess.run(['/usr/bin/patch', '-s', '-p1', '-d', str(w)], stdin=patch, check=True)
    if '${PLIST.tests}bin/gr2fonttest' not in (export/'PLIST').read_text():
        raise SystemExit('graphite test utility is not controlled by its PLIST option')
    fixtures.append(((export/'Makefile').read_text(), 'CMAKE_CONFIGURE_ARGS',
                     '-DBUILD_TESTING=ON', '-DBUILD_TESTING=OFF'))
    for index, (source, variable, on, off) in enumerate(fixtures):
        source = '\n'.join('' if line.lstrip().startswith('.include ') else line
                           for line in source.splitlines())
        for options, enabled in (('', False), ('tests', True)):
            f = w/f'fixture-{index}.mk'
            f.write_text('OPSYS=NetBSD\nPKG_OPTIONS=' + options + '\n' + source +
                         '\nshow:\n\t@printf "%s\\n" "${' + variable + '}"\n')
            r = subprocess.run([str(a.bmake), '-r', '-m', '/', '-f', str(f), 'show'],
                               text=True, capture_output=True, check=True)
            expected = on if enabled else off
            if expected not in r.stdout.split():
                raise SystemExit('wrong option for fixture ' + str(index))
    with tarfile.open(a.distdir/'graphite2-1.3.15.tgz') as archive:
        original = archive.extractfile('graphite2-1.3.15/CMakeLists.txt').read()
    (w/'CMakeLists.txt').write_bytes(original)
    with (root/'profiles/common-build-tools/patches/graphite2-test-tool.patch').open('rb') as patch:
        subprocess.run(['/usr/bin/patch', '-s', '-p1', '-d', str(w)], stdin=patch, check=True)
    result = (w/'CMakeLists.txt').read_text()
    if 'if (BUILD_TESTING AND NOT GRAPHITE2_NFILEFACE)' not in result:
        raise SystemExit('graphite test tool guard missing')
    if 'if (NOT GRAPHITE2_NFILEFACE)' in result:
        raise SystemExit('unguarded graphite test tool')
print('PASS: Qt dependency test options and graphite tool source guard')
