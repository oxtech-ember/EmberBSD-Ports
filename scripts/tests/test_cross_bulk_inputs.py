#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check which recipe changes keep the cross-bulk build-input digest."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'cross-bulk-inputs.py'
NAMES = ('PKGPATH PATCHDIR FILESDIR DISTINFO_FILE LOCALPATCHES CFLAGS CONFIGURE_ARGS '
         '.MAKE.MAKEFILES PKGNAME .CURDIR')


def fixture(root):
    (root / 'mk').mkdir(parents=True)
    (root / 'mk/bsd.pkg.mk').write_text('# infrastructure\nPKGNAME?= ${DISTNAME}\n')
    recipe = root / 'cat/demo'
    (recipe / 'patches').mkdir(parents=True)
    (recipe / 'files').mkdir()
    (recipe / 'Makefile').write_text(
        'DISTNAME=\tdemo-1.0\n'
        'PKGREVISION=\t${DEMO_REVISION}\n'
        '.include "common.mk"\n'
        '.include "../../mk/bsd.pkg.mk"\n')
    (recipe / 'common.mk').write_text('# Shared by the demo packages.\nDEMO_REVISION=\t4\n')
    (recipe / 'distinfo').write_text('SHA1 (demo-1.0.tar.gz) = 00\n')
    (recipe / 'patches/patch-a').write_text('--- a\n+++ b\n')
    (recipe / 'files/demo.sh').write_text('#!/bin/sh\n')


def digest(root, conf, wrkdir, revision='4', **override):
    recipe = root / 'cat/demo'
    values = {
        'PKGPATH': 'cat/demo', 'PATCHDIR': str(recipe / 'patches'),
        'FILESDIR': str(recipe / 'files'), 'DISTINFO_FILE': str(recipe / 'distinfo'),
        'LOCALPATCHES': '', 'CFLAGS': '-O2 -I' + str(root / 'cat/demo/files'),
        'CONFIGURE_ARGS': '--prefix=/usr/pkg',
        '.MAKE.MAKEFILES': 'Makefile common.mk ../../mk/bsd.pkg.mk ' + str(conf),
        'PKGNAME': 'demo-1.0nb' + revision, '.CURDIR': str(recipe)}
    values.update(override)
    stdin = '\n'.join(values[name] for name in NAMES.split()) + '\n'
    result = subprocess.run([sys.executable, '-B', '-E', '-S', str(script), '--pkgsrc', str(root),
                             '--wrkdir', str(wrkdir), '--names', NAMES],
                            input=stdin, capture_output=True, text=True)
    if override.get('expect_error'):
        return result
    assert result.returncode == 0, result.stderr
    value = result.stdout.strip()
    assert len(value) == 64 and all(c in '0123456789abcdef' for c in value), value
    return value


def edit(path, old, new):
    text = path.read_text()
    assert old in text, (path, old)
    path.write_text(text.replace(old, new))


with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    root = temp / 'export-a/pkgsrc'
    fixture(root)
    conf = temp / 'mk.conf'
    conf.write_text('MAKE_JOBS?=\t4\n')
    work = temp / 'obj/cat/demo/work'
    work.mkdir(parents=True)
    base = digest(root, conf, work)
    recipe = root / 'cat/demo'

    # The same inputs under another export root keep the digest.
    other = temp / 'export-b/pkgsrc'
    shutil.copytree(root, other)
    assert digest(other, conf, work) == base

    # A revision bump through the helper variable, or directly, keeps it.
    edit(recipe / 'common.mk', 'DEMO_REVISION=\t4', 'DEMO_REVISION=\t5')
    assert digest(root, conf, work, revision='5') == base
    edit(recipe / 'Makefile', 'PKGREVISION=\t${DEMO_REVISION}\n', 'PKGREVISION=\t7\n')
    direct = digest(root, conf, work, revision='7')
    edit(recipe / 'Makefile', 'PKGREVISION=\t7\n', 'PKGREVISION=\t8\n')
    assert digest(root, conf, work, revision='8') == direct
    edit(recipe / 'Makefile', 'PKGREVISION=\t8\n', 'PKGREVISION=\t${DEMO_REVISION}\n')
    assert digest(root, conf, work, revision='5') == base

    # Generated makevars in the work directory do not count.
    (work / '.extract_makevars.mk').write_text('PKGNAME_CACHED=demo-1.0nb5\n')
    assert digest(root, conf, work, revision='5', **{
        '.MAKE.MAKEFILES': 'Makefile common.mk ../../mk/bsd.pkg.mk ' + str(conf) + ' ' +
        str(work / '.extract_makevars.mk')}) == base

    def changed(apply, revert, **override):
        apply()
        try:
            assert digest(root, conf, work, revision='5', **override) != base
        finally:
            revert()
        assert digest(root, conf, work, revision='5') == base

    # Every other input change gives another digest.
    changed(lambda: edit(recipe / 'Makefile', '.include "common.mk"', '# nb6: provider ABI\n.include "common.mk"'),
            lambda: edit(recipe / 'Makefile', '# nb6: provider ABI\n.include "common.mk"', '.include "common.mk"'))
    changed(lambda: edit(recipe / 'patches/patch-a', '+++ b\n', '+++ b\n+fix\n'),
            lambda: edit(recipe / 'patches/patch-a', '+++ b\n+fix\n', '+++ b\n'))
    changed(lambda: edit(recipe / 'distinfo', '= 00', '= 01'), lambda: edit(recipe / 'distinfo', '= 01', '= 00'))
    changed(lambda: edit(recipe / 'files/demo.sh', '#!/bin/sh', '#!/bin/ksh'),
            lambda: edit(recipe / 'files/demo.sh', '#!/bin/ksh', '#!/bin/sh'))
    changed(lambda: edit(root / 'mk/bsd.pkg.mk', 'infrastructure', 'framework'),
            lambda: edit(root / 'mk/bsd.pkg.mk', 'framework', 'infrastructure'))
    changed(lambda: edit(conf, '4', '8'), lambda: edit(conf, '8', '4'))
    (recipe / 'PLIST').write_text('bin/demo\n')
    plist = digest(root, conf, work, revision='5')
    assert plist != base
    (recipe / 'PLIST').unlink()
    assert digest(root, conf, work, revision='5') == base
    assert digest(root, conf, work, revision='5', CFLAGS='-O3') != base
    # A conditional revision is a recipe change.
    changed(lambda: edit(recipe / 'Makefile', 'PKGREVISION=\t${DEMO_REVISION}\n',
                         '.if ${OPSYS} == "Darwin"\nPKGREVISION=\t${DEMO_REVISION}\n.endif\n'),
            lambda: edit(recipe / 'Makefile', '.if ${OPSYS} == "Darwin"\nPKGREVISION=\t${DEMO_REVISION}\n.endif\n',
                         'PKGREVISION=\t${DEMO_REVISION}\n'))
    # A helper revision variable that the build also uses is a build input.
    edit(recipe / 'Makefile', '.include "common.mk"', '.include "common.mk"\nCONFIGURE_ARGS+= --build-id=${DEMO_REVISION}')
    used = digest(root, conf, work, revision='5')
    edit(recipe / 'common.mk', 'DEMO_REVISION=\t5', 'DEMO_REVISION=\t6')
    assert digest(root, conf, work, revision='6') != used
    edit(recipe / 'Makefile', '.include "common.mk"\nCONFIGURE_ARGS+= --build-id=${DEMO_REVISION}', '.include "common.mk"')
    edit(recipe / 'common.mk', 'DEMO_REVISION=\t6', 'DEMO_REVISION=\t5')
    assert digest(root, conf, work, revision='5') == base
    # A recipe that names PKGVERSION may compile the revision in.
    edit(recipe / 'Makefile', '.include "common.mk"', '.include "common.mk"\nCPPFLAGS+= -DVERSION=\\"${PKGVERSION}\\"')
    named = digest(root, conf, work, revision='5')
    assert digest(root, conf, work, revision='6') != named
    edit(recipe / 'Makefile', '.include "common.mk"\nCPPFLAGS+= -DVERSION=\\"${PKGVERSION}\\"', '.include "common.mk"')
    # PKGVERSION_NOREV and PKGNAME_NOREV do not name the revision.
    edit(recipe / 'Makefile', '.include "common.mk"', '.include "common.mk"\nDIST_SUBDIR= ${PKGNAME_NOREV}')
    noref = digest(root, conf, work, revision='5')
    assert digest(root, conf, work, revision='6') == noref
    edit(recipe / 'Makefile', '.include "common.mk"\nDIST_SUBDIR= ${PKGNAME_NOREV}', '.include "common.mk"')
    assert digest(root, conf, work, revision='5') == base

    # Incomplete answers give no digest.
    for override in ({'.CURDIR': str(temp / 'elsewhere')},):
        result = digest(root, conf, work, revision='5', expect_error=True, **override)
        assert result.returncode == 1 and result.stdout == '', result
    result = subprocess.run([sys.executable, '-B', '-E', '-S', str(script), '--pkgsrc', str(root),
                             '--names', NAMES], input='one\n', capture_output=True, text=True)
    assert result.returncode == 1 and result.stdout == '' and 'one value line' in result.stderr
    result = subprocess.run([sys.executable, '-B', '-E', '-S', str(script), '--pkgsrc', str(root),
                             '--names', 'PKGPATH'], input='cat/demo\n', capture_output=True, text=True)
    assert result.returncode == 1 and result.stdout == '' and 'missing variable' in result.stderr
print('PASS: revision-only edits keep the build-input digest; source, patch, file, recipe, '
      'infrastructure, configuration, option and revision-dependent changes change it')
