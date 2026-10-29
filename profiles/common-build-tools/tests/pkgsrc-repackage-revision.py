#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise an actual pkgsrc package then repackage after PKGREVISION changes."""
import argparse
from pathlib import Path
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--expect-failure', action='store_true', help='negative check of an unpatched export')
a = p.parse_args()
pkgsrc = a.pkgsrc.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='pkgsrc-repackage-revision-') as td:
    root = Path(td); tree = root / 'pkgsrc'; tree.mkdir()
    for item in pkgsrc.iterdir():
        if item.name != 'misc':
            (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
    fixture = tree / 'misc/ember-repackage-fixture'; fixture.mkdir(parents=True)
    (fixture / 'Makefile').write_text('''DISTNAME= ember-repackage-fixture-1.0
PKGREVISION?= 1
CATEGORIES= misc
COMMENT= Small pkgsrc repackage regression fixture
LICENSE= 2-clause-bsd
DISTFILES=
NO_CHECKSUM= yes
NO_EXTRACT= yes
NO_CONFIGURE= yes
NO_BUILD= yes
WRKSRC= ${WRKDIR}
do-install:
\t${MKDIR} ${DESTDIR}${PREFIX}/share/ember-repackage-fixture
\t${ECHO} revision-${PKGREVISION}-${FIXTURE_MARKER} > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/revision
\tcase " $$MAKEFLAGS " in *" -s "*) ${ECHO} silent;; *) ${ECHO} missing;; esac > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/flags
.include "../../mk/bsd.pkg.mk"
''')
    (fixture / 'DESCR').write_text('Small repackage regression fixture.\n')
    (fixture / 'PLIST').write_text('@comment fixture\nshare/ember-repackage-fixture/revision\nshare/ember-repackage-fixture/flags\n')
    command = [str(a.bmake.resolve(strict=True)), '-s', '-C', str(fixture),
               'MAKECONF=' + str(a.makeconf.resolve(strict=True)),
               'EMBERBSD_PKGSRCDIR=' + str(pkgsrc),
               'WRKOBJDIR=' + str(root / 'work'), 'PACKAGES=' + str(root / 'packages'),
               'FIXTURE_MARKER=selected setting']
    def run(revision, target):
        return subprocess.run(command + ['PKGREVISION=' + revision, target],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=180)
    initial = run('1', 'package')
    if initial.returncode:
        raise SystemExit('initial package failed:\n' + initial.stdout[-3000:])
    changed = run('2', 'repackage')
    if a.expect_failure:
        if changed.returncode == 0 or 'don\'t know how to make generate-wrappers' not in changed.stdout:
            raise SystemExit('old barrier failure was not reproduced:\n' + changed.stdout[-3000:])
        print('PASS: old export rejects changed revision at wrapper barrier')
    else:
        if changed.returncode:
            raise SystemExit('repackage failed:\n' + changed.stdout[-3000:])
        archive = root / 'packages/All/ember-repackage-fixture-1.0nb2.tgz'
        with tarfile.open(archive, 'r:gz') as tar:
            metadata = tar.extractfile('+CONTENTS').read().decode()
            payload = tar.extractfile('share/ember-repackage-fixture/revision').read().decode()
            flags = tar.extractfile('share/ember-repackage-fixture/flags').read().decode()
        if '@name ember-repackage-fixture-1.0nb2\n' not in metadata or payload != 'revision-2-selected setting\n' or flags != 'silent\n':
            raise SystemExit('rebuilt package metadata or payload differs')
        print('PASS: revision change re-enters barrier and rebuilds selected package payload')
