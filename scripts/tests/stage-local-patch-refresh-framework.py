#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Refresh across equal exported frameworks with the selected real bmake."""
import argparse
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--patch', type=Path, required=True)
parser.add_argument('--bmake', type=Path, required=True)
args = parser.parse_args()
helper = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'

with tempfile.TemporaryDirectory(prefix='refresh-framework-test-') as temporary:
    root = Path(temporary)
    recipe = root / 'current/cat/demo'
    previous = root / 'old-export/cat/demo'
    work = root / 'work'
    source = work / 'demo-1'
    source.mkdir(parents=True)
    archive = root / 'demo-1.tar.xz'
    with tarfile.open(archive, 'w:xz') as stream:
        data = b'base\n'
        entry = tarfile.TarInfo('demo-1/input')
        entry.size = len(data)
        entry.mode = 0o644
        stream.addfile(entry, io.BytesIO(data))
    data = archive.read_bytes()
    archive_info = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\n'
                    f'SHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\n'
                    f'Size ({archive.name}) = {len(data)} bytes\n')
    old = b'--- input\n+++ input\n@@ -1 +1 @@\n-base\n+old\n'
    new = old.replace(b'+old', b'+new')
    values = {'WRKDIR': work, 'WRKSRC': source, 'PATCH': args.patch,
              'PATCH_ARGS': f'-d {source} -E -p0 --batch --forward -V simple -z .orig',
              'DISTDIR': root, 'DIST_SUBDIR': '', 'DISTFILES': archive.name,
              'DISTNAME': 'demo-1', 'PKG_DBDIR': root / 'pkgdb', 'CROSS_DESTDIR': '',
              'PKGBASE': 'demo', 'PKGNAME': 'demo-1', 'PKGVERSION_NOREV': '1',
              'PATCHFILES': '', 'PATCHDIR': recipe / 'patches',
              'DISTINFO_FILE': recipe / 'distinfo', 'EXTRACT_ONLY': archive.name,
              'EXTRACT_USING': 'bsdtar', 'EXTRACT_SUFX': '.tar.xz',
              'EXTRACT_CMD': '/selected/bsdtar', 'EXTRACT_ENV': '',
              'EXTRACT_BEFORE_ARGS': '-xf', 'EXTRACT_AFTER_ARGS': '',
              'LOCALPATCHES': '', 'META_PACKAGE': '', 'SUBST_CLASSES': '',
              'PKG_FAIL_REASON': ''}
    makefile = ''.join(f'{key}= {value}\n' for key, value in values.items())
    makefile += ('.include "${.PARSEDIR}/../../mk/bsd.prefs.mk"\n'
                 '.include "${.PARSEDIR}/../../mk/patch/patch.mk"\n'
                 '.include "${.PARSEDIR}/../../mk/extract/extract.mk"\n'
                 'show-vars:\n.for name in ${VARNAMES}\n'
                 '\t@printf "%s\\n" \'${${name}}\'\n.endfor\n'
                 'pre-patch post-patch pre-extract post-extract:\n'
                 f'configure-clean:\n\t@touch {root / "clean"}\n')
    framework = {'mk/bsd.prefs.mk': b'# framework preferences\n',
                 'mk/patch/patch.mk': b'do-patch:\n\t@true\n',
                 'mk/extract/extract.mk': b'do-extract:\n\t@true\n'}
    for directory, patch in ((previous, old), (recipe, new)):
        (directory / 'patches').mkdir(parents=True)
        (directory / 'Makefile').write_text(makefile)
        (directory / 'patches/patch-a').write_bytes(patch)
        (directory / 'distinfo').write_text(
            archive_info + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n')
        for relative, contents in framework.items():
            path = directory.parents[1] / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
    owner = root / 'pkgdb/demo-1nb1/+BUILD_VERSION'
    owner.parent.mkdir(parents=True)
    def provenance():
        owner.write_text(''.join(f'cat/demo/{name}: {hashlib.sha256((previous / name).read_bytes()).hexdigest()}\n'
                                for name in ('Makefile', 'distinfo', 'patches/patch-a')))
    provenance()
    (work / '.patch_done').write_text(str(recipe / 'patches/patch-a') + '\n')
    (source / 'input').write_bytes(b'old\n')
    (source / 'object.o').write_bytes(b'keep\n')
    object_time = (source / 'object.o').stat().st_mtime_ns
    command = [sys.executable, '-B', str(helper), '--sdk-source', str(args.sdk_source),
               '--bmake', str(args.bmake), '--native', '--recipe', str(recipe),
               '--expected-work', str(work), '--previous-recipe', str(previous)]
    # Same framework bytes under another export root remain standard rules.
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (source / 'input').read_bytes() == b'new\n'
    assert (source / 'object.o').stat().st_mtime_ns == object_time
    assert (root / 'clean').is_file()
    (root / 'clean').unlink()
    (source / 'input').write_bytes(b'old\n')
    for relative in framework:
        path = previous.parents[1] / relative
        original = path.read_bytes()
        path.write_bytes(original + b'# changed old framework\n')
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode and 'previous framework differs' in result.stderr, result.stderr
        assert (source / 'input').read_bytes() == b'old\n' and not (root / 'clean').exists()
        path.write_bytes(original)
    # A provenance-bound recipe target is still not a framework target.
    (previous / 'Makefile').write_text(makefile + 'do-patch: custom\ncustom:\n\t@true\n')
    provenance()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'active custom do-patch' in result.stderr, result.stderr
    assert (source / 'input').read_bytes() == b'old\n' and not (root / 'clean').exists()
    # A framework input changed after validation must fail before live writes.
    old_prefs = previous.parents[1] / 'mk/bsd.prefs.mk'
    (previous / 'Makefile').write_text(makefile +
        '.if "${VARNAMES:U}" == "PKG_FAIL_REASON"\n' +
        f'DRIFT!= echo DRIFT=yes >> {old_prefs}\n.endif\n')
    provenance()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'recipe input changed during source replay' in result.stderr, result.stderr
    assert (source / 'input').read_bytes() == b'old\n' and not (root / 'clean').exists()
print('PASS: equal old-export framework, changed framework, custom target and replay drift rejection')
