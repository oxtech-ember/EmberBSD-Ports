#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise metadata-only repackaging with real pkgsrc and no C compiler."""
import argparse
import sys
from pathlib import Path
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('pkgsrc', 'makeconf', 'bmake', 'patch', 'patch-file'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--inject-identity-fault', action='store_true', help='negative control for the identity guard')
a = p.parse_args()
source = a.pkgsrc.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='pkgsrc-repackage-metadata-') as td:
    root = Path(td); tree = root / 'pkgsrc'; tree.mkdir()
    for item in source.iterdir():
        if item.name not in ('mk', 'misc'):
            (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
    def overlay(src, dst, exclude):
        dst.mkdir()
        for child in src.iterdir():
            if child.name not in exclude:
                (dst / child.name).symlink_to(child, target_is_directory=child.is_dir())
    overlay(source / 'mk', tree / 'mk', {'package', 'install', 'bsd.pkg.barrier.mk'})
    (tree / 'mk/bsd.pkg.barrier.mk').write_bytes((source / 'mk/bsd.pkg.barrier.mk').read_bytes())
    for part, changed in [('package', 'bsd.package.mk'), ('install', 'install.mk')]:
        overlay(source / 'mk' / part, tree / 'mk' / part, {changed})
        (tree / 'mk' / part / changed).write_bytes((source / 'mk' / part / changed).read_bytes())
    result = subprocess.run([str(a.patch), '-p1', '-i', str(a.patch_file.resolve())], cwd=tree,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise SystemExit('patch failed:\n' + result.stdout)
    if a.inject_identity_fault:
        helper = tree / 'mk/package/repackage-metadata-check.py'
        text = helper.read_text()
        before = 'fail("different package, upstream version or invalid revision")'
        if before not in text:
            raise SystemExit('identity negative control could not be injected')
        helper.write_text(text.replace(before, 'continue'))
    fixture = tree / 'misc/ember-repackage-fixture'; fixture.mkdir(parents=True)
    (fixture / 'Makefile').write_text('''FIX_VERSION?= 1.0
DISTNAME= ember-repackage-fixture-${FIX_VERSION}
PKGREVISION?= 1
CATEGORIES= misc
COMMENT= Metadata-only repackage regression fixture
LICENSE= 2-clause-bsd
DISTFILES=
NO_CHECKSUM= yes
NO_EXTRACT= yes
.if !defined(FIX_CONFIGURE)
NO_CONFIGURE?= yes
.endif
WRKSRC= ${WRKDIR}
do-configure:
\t${DO_NADA}
do-build:
\t${ECHO} build >> ${BUILD_RECORD:Q}
\t${ECHO} compiled > ${WRKSRC}/compiled

do-install:
\t${TEST} "${FAIL_INSTALL:Uno}" != yes
\t${MKDIR} ${DESTDIR}${PREFIX}/share/ember-repackage-fixture
\t${CP} ${WRKSRC}/compiled ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/compiled
\t${ECHO} revision-${PKGREVISION}-barrier-${_PKGSRC_BARRIER:Uno} > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/revision
\tif [ ${PKGREVISION} = 2 ]; then ${ECHO} added > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/added; fi
.include "../../mk/bsd.pkg.mk"
''')
    (fixture / 'DESCR').write_text('Metadata repackage regression.\n')
    plist = fixture / 'PLIST'
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\n')
    record = root / 'builds'; work = root / 'work/misc/ember-repackage-fixture/work'
    cmd = [str(a.bmake.resolve()), '-s', '-C', str(fixture), 'MAKECONF=' + str(a.makeconf.resolve()),
           'EMBERBSD_PKGSRCDIR=' + str(tree), 'EMBERBSD_REPACKAGE_PYTHON=' + sys.executable,
           'WRKOBJDIR=' + str(root / 'work'), 'PACKAGES=' + str(root / 'packages'),
           'BUILD_RECORD=' + str(record)]
    def run(target, *args):
        return subprocess.run(cmd + list(args) + [target], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=180)
    def require(ok, msg, result=None):
        if not ok: raise SystemExit(msg + ('\n' + result.stdout[-3500:] if result else ''))
    r = run('package', 'PKGREVISION=1'); require(r.returncode == 0, 'initial package failed', r)
    require(not any(x in r.stdout for x in ('unexpected operator', 'missing ]', 'unknown operand')), 'ordinary install emitted shell diagnostic', r)
    require(record.read_text().splitlines() == ['build'], 'initial build count')
    old = [(work / x).read_text() for x in ('.extract_done', '.build_done')]
    # First validate failure occurs before existing stage or package is removed.
    stage = work / '.destdir'; require(stage.is_dir(), 'missing original stage')
    sentinel = stage / 'must-survive-refusal'; sentinel.write_text('unchanged')
    for interpreter in ('', 'python3.15'):
        r = run('repackage-metadata', 'PKGREVISION=2', 'EMBERBSD_REPACKAGE_PYTHON=' + interpreter)
        require(r.returncode != 0 and sentinel.is_file(), 'invalid interpreter accepted', r)
    for args in [('PKGREVISION=2','FIX_VERSION=2.0'), ('PKGREVISION=bogus',)]:
        r = run('repackage-metadata', *args); require(r.returncode != 0 and sentinel.is_file(), 'invalid identity accepted or stage removed', r)
    r = run('repackage-metadata','PKGREVISION=2','WRKSRC=' + str(root / 'missing-source'))
    require(r.returncode != 0 and sentinel.is_file(), 'missing source accepted', r)
    extract = work / '.extract_done'; extract_bytes = extract.read_bytes(); extract.unlink()
    r = run('repackage-metadata','PKGREVISION=2'); require(r.returncode != 0 and sentinel.is_file(), 'missing extract accepted', r); extract.write_bytes(extract_bytes)
    build = work / '.build_done'; saved = build.read_bytes(); build.unlink()
    r = run('repackage-metadata','PKGREVISION=2'); require(r.returncode != 0 and sentinel.is_file(), 'missing build accepted', r);build.write_bytes(saved)
    build.write_text('ember-repackage-fixture-1.0nb9\n')
    r = run('repackage-metadata','PKGREVISION=2'); require(r.returncode != 0 and sentinel.is_file(), 'inconsistent cookies accepted', r); build.write_bytes(saved)
    extract = work / '.extract_done'; extract_saved = extract.read_bytes()
    for wrong in ('other-package-1.0nb1\n', 'ember-repackage-fixture-1.0nb1tail\n'):
        extract.write_text(wrong); build.write_text(wrong)
        r = run('repackage-metadata','PKGREVISION=2'); require(r.returncode != 0 and sentinel.is_file(), 'wrong cookie accepted', r)
    extract.write_bytes(extract_saved); build.write_bytes(saved)
    configure = work / '.configure_done'; configure_saved = configure.read_bytes(); configure.unlink()
    r = run('repackage-metadata','PKGREVISION=2','FIX_CONFIGURE=yes'); require(r.returncode != 0 and sentinel.is_file(), 'missing configure accepted', r); configure.write_bytes(configure_saved)
    # New packaging recipe adds a file without changing compile inputs.
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\nshare/ember-repackage-fixture/added\n')
    r = run('repackage-metadata','PKGREVISION=2','FAIL_INSTALL=yes');require(r.returncode != 0, 'install failure ignored', r)
    require(record.read_text().splitlines()==['build'], 'recompiled after install failure')
    # Changing PLIST to an uninstalled file must still fail checks.
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\nshare/ember-repackage-fixture/added\nshare/ember-repackage-fixture/missing\n')
    r = run('repackage-metadata','PKGREVISION=2');require(r.returncode != 0, 'PLIST mismatch accepted', r)
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\nshare/ember-repackage-fixture/added\n')
    r = run('repackage-metadata','PKGREVISION=2');require(r.returncode == 0, 'retry failed', r)
    require(record.read_text().splitlines()==['build'], 'metadata operation recompiled')
    require([(work / x).read_text() for x in ('.extract_done','.build_done')] == old, 'build identity changed')
    archive=root/'packages/All/ember-repackage-fixture-1.0nb2.tgz'
    with tarfile.open(archive,'r:*') as tar:
        contents=tar.extractfile('+CONTENTS').read().decode(); payload=tar.extractfile('share/ember-repackage-fixture/revision').read().decode(); added=tar.extractfile('share/ember-repackage-fixture/added').read().decode()
    require('@name ember-repackage-fixture-1.0nb2\n' in contents and payload=='revision-2-barrier-yes\n' and added=='added\n','new metadata/payload incorrect')
    # A mode scoped to another package must not weaken the normal version check.
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\n')
    r = run('repackage', 'PKGREVISION=3', '_EMBER_REPACKAGE_IDENTITY=ember-repackage-fixture-1.0nb1',
            '_EMBER_REPACKAGE_PKGPATH=misc/another-package', '_EMBER_REPACKAGE_WRKDIR=' + str(work))
    require(r.returncode == 0 and record.read_text().splitlines() == ['build', 'build'],
            'foreign metadata scope weakened ordinary repackage', r)
    # Ordinary operation with no internal state must not emit shell test errors.
    r = run('repackage', 'PKGREVISION=4')
    require(r.returncode == 0 and record.read_text().splitlines() == ['build', 'build', 'build'],
            'ordinary repackage without internal state failed', r)
    require(not any(x in r.stdout for x in ('unexpected operator', 'missing ]', 'unknown operand')), 'shell test diagnostic', r)
    # pkgsrc disables configure whenever NO_CONFIGURE is defined, regardless of value.
    configure = work / '.configure_done'
    if configure.exists(): configure.unlink()
    for value in ('yes', 'no', 'YES'):
        stage.mkdir(exist_ok=True); sentinel.write_text('unchanged')
        r = run('repackage-metadata', 'PKGREVISION=5', 'NO_CONFIGURE=' + value, 'FAIL_INSTALL=yes')
        require(r.returncode != 0 and not sentinel.exists() and 'Installing for' in r.stdout,
                'defined NO_CONFIGURE was treated as enabled', r)
    regression = Path(__file__).with_name('pkgsrc-repackage-revision.py')
    r = subprocess.run([sys.executable, '-B', str(regression), '--pkgsrc', str(tree),
                        '--makeconf', str(a.makeconf), '--bmake', str(a.bmake)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    require(r.returncode == 0, 'ordinary repackage regression failed on patched overlay', r)
    print('PASS: identity refusals, install/PLIST failures and retry; revision repackaged without rebuilding')
    print(r.stdout.strip())
