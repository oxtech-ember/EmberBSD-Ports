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
for name in ('pkgsrc', 'upstream-pkgsrc', 'makeconf', 'bmake', 'patch', 'barrier-patch', 'patch-file', 'sdk-source'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--inject-identity-fault', action='store_true', help='negative control for the identity guard')
a = p.parse_args()
source = a.pkgsrc.resolve(strict=True)
upstream = a.upstream_pkgsrc.resolve(strict=True)
sdk_source = a.sdk_source.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='pkgsrc-repackage-metadata-') as td:
    root = Path(td); tree = root / 'pkgsrc'; tree.mkdir()
    resolver_log = root / 'resolver-calls'
    resolver_python = root / 'resolver-python'
    resolver_python.write_text(
        '#!' + sys.executable + '\n'
        'import os, sys\n'
        'if any(arg.endswith("resolve-jobs.py") for arg in sys.argv):\n'
        '    with open(' + repr(str(resolver_log)) + ', "a", encoding="utf-8") as stream:\n'
        '        stream.write("resolve\\n")\n'
        'os.execv(' + repr(sys.executable) + ', [' + repr(sys.executable) + ', *sys.argv[1:]])\n')
    resolver_python.chmod(0o755)
    for item in source.iterdir():
        if item.name not in ('mk', 'misc'):
            (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
    def overlay(src, dst, exclude):
        dst.mkdir()
        for child in src.iterdir():
            if child.name not in exclude:
                (dst / child.name).symlink_to(child, target_is_directory=child.is_dir())
    overlay(source / 'mk', tree / 'mk', {'package', 'install', 'build', 'bsd.pkg.barrier.mk'})
    (tree / 'mk/bsd.pkg.barrier.mk').write_bytes((upstream / 'mk/bsd.pkg.barrier.mk').read_bytes())
    for part, changed in [('package', {'bsd.package.mk', 'repackage-metadata-check.py'}),
                          ('install', {'install.mk'})]:
        overlay(source / 'mk' / part, tree / 'mk' / part, changed)
        for filename in changed:
            if filename == 'repackage-metadata-check.py':
                continue
            (tree / 'mk' / part / filename).write_bytes((upstream / 'mk' / part / filename).read_bytes())
    overlay(source / 'mk/build', tree / 'mk/build', {'build.mk'})
    (tree / 'mk/build/build.mk').write_bytes((upstream / 'mk/build/build.mk').read_bytes())
    # The upstream input may be pristine or may already contain the exact
    # previously published install re-entry hunk. Normalize only that known
    # hunk in this private tree; reject any other starting state.
    old_install = root / 'previous-install-hunk.patch'
    old_install.write_text("\n".join((
        '--- a/mk/install/install.mk',
        '+++ b/mk/install/install.mk',
        '@@ -159,6 +159,8 @@',
        ' \t\t${WARNING_MSG} "Current version $$pkgname in ${PKGPATH}"; \\',
        ' \t\t${WARNING_MSG} "Cleaning and rebuilding $$pkgname...";\t\\',
        ' \t\t${RECURSIVE_MAKE} ${MAKEFLAGS} clean;\t\t\t\\',
        '+\t\tunset _PKGSRC_BARRIER;\t\t\t\t\t\\',
        '+\t\tMAKEFLAGS=${.MAKEFLAGS:Q} \t\t\t\t\\',
        ' \t\t${RECURSIVE_MAKE} ${MAKEFLAGS} build ;;\t\t\t\\',
        ' \tesac',
        ' ',
    )) + '\n')
    current_install = root / 'current-install-hunk.patch'
    install_marker = '--- a/mk/install/install.mk\n'
    barrier_text = a.barrier_patch.read_text()
    if install_marker not in barrier_text:
        raise SystemExit('barrier patch has no install re-entry hunk')
    current_install.write_text(install_marker + barrier_text.split(install_marker, 1)[1])
    previous = subprocess.run([str(a.patch), '--batch', '-R', '--dry-run', '-p1', '-F0',
                               '-i', str(old_install)], cwd=tree,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if previous.returncode == 0:
        result = subprocess.run([str(a.patch), '--batch', '-R', '-p1', '-F0',
                                 '-i', str(old_install)], cwd=tree,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode:
            raise SystemExit('cannot reverse the known prior install hunk:\n' + result.stdout)
    else:
        current = subprocess.run([str(a.patch), '--batch', '--forward', '--dry-run', '-p1', '-F0',
                                  '-i', str(current_install)], cwd=tree,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if current.returncode:
            raise SystemExit('upstream install.mk is neither pristine nor the known prior patch:\n' +
                             current.stdout)
    for patch_file in (a.barrier_patch, a.patch_file):
        result = subprocess.run([str(a.patch), '--batch', '--forward', '-p1', '-F0',
                                 '-i', str(patch_file.resolve())], cwd=tree,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode:
            raise SystemExit('patch failed:\n' + result.stdout)
    if a.inject_identity_fault:
        helper = tree / 'mk/package/repackage-metadata-check.py'
        text = helper.read_text()
        before = 'fail("different package or upstream version")'
        if before not in text:
            raise SystemExit('identity negative control could not be injected')
        helper.write_text(text.replace(before, 'return 0'))
    fixture = tree / 'misc/ember-repackage-fixture'; fixture.mkdir(parents=True)
    (fixture / 'Makefile').write_text('''FIX_VERSION?= 1.0
DISTNAME= ember-repackage-fixture-${FIX_VERSION}
PKGREVISION?= 1
CATEGORIES= misc
COMMENT= Metadata-only repackage regression fixture
LICENSE= 2-clause-bsd
DISTFILES=
NO_CHECKSUM= yes
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
\t${ECHO} ${MAKE_JOBS:Uunset} >> ${JOBS_RECORD:Q}
\t${MKDIR} ${DESTDIR}${PREFIX}/share/ember-repackage-fixture
\t${ECHO} ${PKGNAME}-barrier-${_PKGSRC_BARRIER:Uno} >> ${INSTALL_RECORD:Q}
\t${CP} ${WRKSRC}/compiled ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/compiled
\t${ECHO} revision-${PKGREVISION}-barrier-${_PKGSRC_BARRIER:Uno} > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/revision
\tif [ ${PKGREVISION} = 2 ]; then ${ECHO} added > ${DESTDIR}${PREFIX}/share/ember-repackage-fixture/added; fi
.include "../../mk/bsd.pkg.mk"
''')
    (fixture / 'DESCR').write_text('Metadata repackage regression.\n')
    plist = fixture / 'PLIST'
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\n')
    record = root / 'builds'; job_record = root / 'install-jobs'
    work = None
    cmd = [str(a.bmake.resolve()), '-s', '-C', str(fixture), 'MAKECONF=' + str(a.makeconf.resolve()),
           'EMBERBSD_PKGSRCDIR=' + str(tree), 'EMBERBSD_REPACKAGE_PYTHON=' + sys.executable,
           'EMBERBSD_HOST_PYTHON=' + str(resolver_python), 'EMBERBSD_SDK_SOURCE=' + str(sdk_source),
           'WRKOBJDIR=' + str(root / 'work'), 'PACKAGES=' + str(root / 'packages'),
           'BUILD_RECORD=' + str(record), 'JOBS_RECORD=' + str(job_record),
           'INSTALL_RECORD=' + str(root / 'install-record')]
    def run(target, *args):
        args = list(args)
        if not any(x.startswith('MAKE_JOBS=') for x in args):
            args.append('MAKE_JOBS=')
        return subprocess.run(cmd + args + [target], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=180)
    def require(ok, msg, result=None):
        if not ok: raise SystemExit(msg + ('\n' + result.stdout[-3500:] if result else ''))
    def resolver_count():
        return len(resolver_log.read_text().splitlines()) if resolver_log.exists() else 0
    reentry = root / 'reentry with spaces'; reentry.mkdir()
    reentry_result = reentry / 'values.txt'
    child_makefile = reentry / 'child.mk'
    child_makefile.write_text('''.PHONY: nested
nested:
\t@echo "${PKGREVISION:Uunset}" > ${RESULT:Q}
\t@echo "${SPACED:Uunset}" >> ${RESULT:Q}
\t@echo "${MAKE_JOBS:Uunset}" >> ${RESULT:Q}
\t@echo "${_PKGSRC_BARRIER:Uunset}" >> ${RESULT:Q}
\t@echo "${PACKAGE_FLAG:Uunset}" >> ${RESULT:Q}
''')
    parent_makefile = reentry / 'parent.mk'
    parent_makefile.write_text('''MAKEFLAGS+= PACKAGE_FLAG=from-pkgsrc
.PHONY: reenter
reenter:
\tunset _PKGSRC_BARRIER; MAKEFLAGS=${.MAKEFLAGS:Q} ${RECURSIVE_MAKE} ${MAKEFLAGS} ${.MAKEOVERRIDES:N_PKGSRC_BARRIER:@v@${v}=${${v}:Q}@} -f ${CHILD:Q} nested
''')
    r = subprocess.run([str(a.bmake.resolve()), '-s', '-f', str(parent_makefile),
                        'RECURSIVE_MAKE=' + str(a.bmake.resolve()),
                        'CHILD=' + str(child_makefile), 'RESULT=' + str(reentry_result),
                        'PKGREVISION=3', 'SPACED=' + str(reentry), 'MAKE_JOBS=',
                        '_PKGSRC_BARRIER=yes', 'reenter'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
    require(r.returncode == 0, 'nested re-entry fixture failed', r)
    require(reentry_result.read_text().splitlines() ==
            ['3', str(reentry), '', 'unset', 'from-pkgsrc'],
            'nested re-entry lost a pkgsrc MAKEFLAGS value, override, spaced path, empty value, or barrier reset')
    def query_wrkdir(fixture, wrkobjdir):
        result = subprocess.run([str(a.bmake.resolve()), '-s', '-C', str(fixture),
                                 'MAKECONF=' + str(a.makeconf.resolve()),
                                 'EMBERBSD_PKGSRCDIR=' + str(tree),
                                 'WRKOBJDIR=' + str(wrkobjdir), 'show-var', 'VARNAME=WRKDIR'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=60)
        require(result.returncode == 0 and result.stdout.strip(), 'cannot query fixture WRKDIR', result)
        return Path(result.stdout.strip())
    def query_var(name, *args):
        result = subprocess.run(cmd + list(args) + ['show-var', 'VARNAME=' + name],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=60)
        require(result.returncode == 0, 'cannot query ' + name, result)
        return result.stdout.strip()
    require(query_var('_MAKE_JOBS', 'MAKE_JOBS=') == '',
            'empty MAKE_JOBS produced a bare -j option')
    require(query_var('_MAKE_JOBS', 'MAKE_JOBS=2') == '-j2',
            'positive MAKE_JOBS no longer produces the expected -j option')
    r = run('package', 'PKGREVISION=1'); require(r.returncode == 0, 'initial package failed', r)
    work = query_wrkdir(fixture, root / 'work')
    require(not any(x in r.stdout for x in ('unexpected operator', 'missing ]', 'unknown operand')), 'ordinary install emitted shell diagnostic', r)
    require(record.read_text().splitlines() == ['build'], 'initial build count')
    require(resolver_count() == 1, 'automatic package build did not resolve jobs exactly once')
    if not (work / '.extract_done').exists():
        (work / '.extract_done').write_text('ember-repackage-fixture-1.0nb1\n')
    expected_jobs = subprocess.check_output(
        [sys.executable, '-B', '-E', '-S', str(sdk_source / 'scripts/resolve-jobs.py')],
        text=True).strip()
    require(job_record.read_text().splitlines()[-1] == expected_jobs,
            'empty MAKE_JOBS did not use the selected SDK CPU resolver at the pkgsrc barrier')
    calls = resolver_count()
    r = run('extract')
    require(r.returncode == 0, 'source-only extract required SDK job inputs', r)
    require(resolver_count() == calls, 'source-only extract invoked the SDK job resolver')
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
    calls = resolver_count()
    r = run('repackage-metadata','PKGREVISION=2');require(r.returncode == 0, 'retry failed', r)
    require(resolver_count() == calls + 1, 'metadata repackage resolved jobs more than once')
    require(record.read_text().splitlines()==['build'], 'metadata operation recompiled')
    require(job_record.read_text().splitlines()[-1] == expected_jobs,
            'empty MAKE_JOBS did not use the selected SDK CPU resolver')
    calls = resolver_count()
    r = run('repackage-metadata', 'PKGREVISION=2', 'MAKE_JOBS=2')
    require(r.returncode == 0, 'explicit job override repackage failed', r)
    require(job_record.read_text().splitlines()[-1] == '2',
            'explicit MAKE_JOBS override was not passed through')
    require(resolver_count() == calls, 'explicit MAKE_JOBS invoked the SDK resolver')
    require([(work / x).read_text() for x in ('.extract_done','.build_done')] == old, 'build identity changed')
    archive=root/'packages/All/ember-repackage-fixture-1.0nb2.tgz'
    with tarfile.open(archive,'r:*') as tar:
        contents=tar.extractfile('+CONTENTS').read().decode(); payload=tar.extractfile('share/ember-repackage-fixture/revision').read().decode(); added=tar.extractfile('share/ember-repackage-fixture/added').read().decode()
    require('@name ember-repackage-fixture-1.0nb2\n' in contents and payload=='revision-2-barrier-yes\n' and added=='added\n','new metadata/payload incorrect')
    # A mode scoped to another package must not weaken the normal version check.
    plist.write_text('share/ember-repackage-fixture/compiled\nshare/ember-repackage-fixture/revision\n')
    r = run('repackage', 'PKGREVISION=3', '_EMBER_REPACKAGE_IDENTITY=ember-repackage-fixture-1.0nb1',
            '_EMBER_REPACKAGE_PKGPATH=misc/another-package', '_EMBER_REPACKAGE_WRKDIR=' + str(work))
    require(r.returncode == 0, 'foreign metadata scope broke ordinary repackage', r)
    require(record.read_text().splitlines() == ['build', 'build'],
            'ordinary version mismatch did not rebuild')
    repackage_archive = root / 'packages/All/ember-repackage-fixture-1.0nb3.tgz'
    require(repackage_archive.is_file(),
            'ordinary repackage did not create nb3 archive; found ' +
            repr(sorted(p.name for p in (root / 'packages/All').glob('ember-repackage-fixture-*'))) +
            '; install calls ' + repr((root / 'install-record').read_text().splitlines()) +
            '\n' + r.stdout[-2500:], r)
    with tarfile.open(repackage_archive, 'r:*') as tar:
        contents = tar.extractfile('+CONTENTS').read().decode()
        payload = tar.extractfile('share/ember-repackage-fixture/revision').read().decode()
    require('@name ember-repackage-fixture-1.0nb3\n' in contents and
            payload == 'revision-3-barrier-yes\n', 'ordinary repackage did not publish current metadata')
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
    ordinary_output = r.stdout.strip()
    # Stage-local package-install may cross a numeric pkgsrc revision only.
    # Its early helper preflight must reject a changed upstream identity before
    # the controller invalidates install/package staging.
    stage = tree / 'misc/ember-stage-local-fixture'; stage.mkdir(parents=True)
    (stage / 'Makefile').write_text('''DISTNAME= ember-stage-local-fixture-1.0
PKGREVISION?= 1
CATEGORIES= misc
COMMENT= Stage-local recovery regression fixture
LICENSE= 2-clause-bsd
DISTFILES= ember-stage-local-fixture.tar
EXTRACT_ONLY= ${DISTFILES}
NO_CHECKSUM= yes
WRKSRC= ${WRKDIR}/source
do-configure:
\t${ECHO} configure >> ${CONFIGURE_RECORD:Q}
do-extract:
\t${MKDIR} ${WRKSRC}
\t${ECHO} extract >> ${EXTRACT_RECORD:Q}
\t${ECHO} ${SOURCE_VALUE:Uold} > ${WRKSRC}/input
do-build:
\t${ECHO} build >> ${BUILD_RECORD:Q}
\t${CP} ${WRKSRC}/input ${WRKSRC}/compiled
do-install:
\t${MKDIR} ${DESTDIR}${PREFIX}/share/ember-stage-local-fixture
\t${CP} ${WRKSRC}/compiled ${DESTDIR}${PREFIX}/share/ember-stage-local-fixture/payload
.include "../../mk/bsd.pkg.mk"
''')
    (stage / 'DESCR').write_text('Stage-local recovery fixture.\n')
    (stage / 'PLIST').write_text('share/ember-stage-local-fixture/payload\n')
    stage_work = None
    stage_builds = root / 'stage-builds'; stage_extracts = root / 'stage-extracts'
    stage_configures = root / 'stage-configures'
    distdir = root / 'distfiles'; distdir.mkdir()
    (distdir / 'ember-stage-local-fixture.tar').write_bytes(b'fixture input\n')
    stage_args = ['WRKOBJDIR=' + str(root / 'work'), 'PACKAGES=' + str(root / 'packages'),
                  'DISTDIR=' + str(distdir),
                  'BUILD_RECORD=' + str(stage_builds), 'EXTRACT_RECORD=' + str(stage_extracts),
                  'CONFIGURE_RECORD=' + str(stage_configures)]
    stage_cmd = [str(a.bmake.resolve()), '-s', '-C', str(stage),
                 'MAKECONF=' + str(a.makeconf.resolve()), 'EMBERBSD_PKGSRCDIR=' + str(tree)] + stage_args
    def stage_run(target, revision='1', *extra):
        return subprocess.run(stage_cmd + list(extra) + ['PKGREVISION=' + revision, target],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    r = stage_run('package')
    require(r.returncode == 0, 'initial stage-local package failed', r)
    stage_work = query_wrkdir(stage, root / 'work')
    require(stage_builds.read_text().splitlines() == ['build'] and
            stage_extracts.read_text().splitlines() == ['extract'], 'initial stage-local phase counts')
    require(stage_configures.read_text().splitlines() == ['configure'], 'initial stage-local configure count')
    helper = tree / 'mk/package/repackage-metadata-check.py'
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(stage_work), 'ember-stage-local-fixture', '1.0',
                        'ember-stage-local-fixture-1.0nb2'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode == 0 and r.stdout.strip() == 'revision',
            'prior package revision was not identified for staging reset', r)
    stage_sentinel = stage_work / '.destdir/must-survive-refusal'
    stage_sentinel.write_text('preserve')
    current_name = 'ember-stage-local-fixture-1.0nb2'
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(stage_work), 'ember-stage-local-fixture', '1.1', current_name],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode != 0 and stage_sentinel.is_file(), 'upstream mismatch changed stage', r)
    cookie_bytes = (stage_work / '.extract_done').read_bytes()
    r = stage_run('install-check-version', '2', '_EMBER_STAGE_LOCAL_PACKAGE_INSTALL=yes',
                  '_EMBER_STAGE_LOCAL_PKGPATH=misc/other', '_EMBER_STAGE_LOCAL_WRKDIR=' + str(stage_work))
    require(r.returncode != 0 and stage_sentinel.is_file(), 'wrong stage-local scope accepted', r)
    require((stage_work / '.extract_done').read_bytes() == cookie_bytes, 'scope refusal changed extract identity')
    r = stage_run('_package-clean')
    require(r.returncode == 0 and not stage_sentinel.exists(), 'stage-local package clean failed', r)
    # A changed source plus pkgsrc's ordinary invalidated build cookie requires
    # one build, while the old compatible extracted tree remains reusable.
    (stage_work / 'source/input').write_text('new-source\n')
    (stage_work / '.build_done').unlink()
    r = stage_run('package', '2', 'SOURCE_VALUE=new-source', '_EMBER_STAGE_LOCAL_PACKAGE_INSTALL=yes',
                  '_EMBER_STAGE_LOCAL_PKGPATH=misc/ember-stage-local-fixture',
                  '_EMBER_STAGE_LOCAL_WRKDIR=' + str(stage_work))
    require(r.returncode == 0, 'stage-local revision recovery failed', r)
    require(stage_builds.read_text().splitlines() == ['build', 'build'], 'stage-local recovery build count')
    require(stage_extracts.read_text().splitlines() == ['extract'], 'stage-local recovery re-extracted source')
    require(stage_configures.read_text().splitlines() == ['configure'], 'stage-local revision recovery reconfigured')
    require((stage_work / '.extract_done').read_bytes() == cookie_bytes, 'stage-local recovery rewrote extract identity')
    stage_archive = root / 'packages/All/ember-stage-local-fixture-1.0nb2.tgz'
    with tarfile.open(stage_archive, 'r:*') as tar:
        payload = tar.extractfile('share/ember-stage-local-fixture/payload').read().decode()
    require(payload == 'new-source\n', 'stage-local package retained stale installed payload')
    # Packaging/test cookies are not build-identity evidence: a stale test
    # cookie cannot admit or reject the otherwise compatible build tree.
    (stage_work / '.test_done').write_text('unrelated-old-test-identity\n')
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(stage_work), 'ember-stage-local-fixture', '1.0',
                        'ember-stage-local-fixture-1.0nb2'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode == 0, 'non-build test cookie affected stage-local identity', r)
    require(r.stdout.strip() == 'same', 'completed package revision would be reset again', r)
    # Missing extract state is fresh only when no later phase cookie survives.
    fresh = root / 'fresh-stage'; fresh.mkdir()
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(fresh), 'ember-stage-local-fixture', '1.0', 'ember-stage-local-fixture-1.0'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode == 0, 'fresh stage was refused', r)
    (fresh / '.test_done').write_text('stale-test-only\n')
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(fresh), 'ember-stage-local-fixture', '1.0', 'ember-stage-local-fixture-1.0'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode == 0 and r.stdout.strip() == 'fresh', 'stale test cookie admitted a stage', r)
    (fresh / '.test_done').unlink()
    (fresh / '.build_done').write_text('ember-stage-local-fixture-1.0nb1\n')
    r = subprocess.run([sys.executable, '-B', '-E', '-S', str(helper), '--stage-local',
                        str(fresh), 'ember-stage-local-fixture', '1.0', 'ember-stage-local-fixture-1.0'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(r.returncode != 0, 'later cookie without extract was accepted', r)
    # An explicit count stays intact through the nested build barrier.
    build_cookie = work / '.build_done'; build_bytes = build_cookie.read_bytes(); build_cookie.unlink()
    calls = resolver_count()
    r = run('build', 'PKGREVISION=4', 'MAKE_JOBS=2')
    require(r.returncode == 0, 'bootstrap build with explicit jobs required SDK Python/source', r)
    require(resolver_count() == calls, 'explicit bootstrap MAKE_JOBS invoked the SDK resolver')
    build_cookie.write_bytes(build_bytes)
    print('PASS: strict metadata-only reuse; stage-local recovery; automatic jobs once; source-only target and explicit nested build avoid another resolver; explicit override preserved')
    print(ordinary_output)
