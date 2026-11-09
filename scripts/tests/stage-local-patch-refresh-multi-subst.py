#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Replay multiple SUBST classes with real bmake and the pkgsrc SUBST owner."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--patch', type=Path, required=True)
p.add_argument('--shell', type=Path, required=True)
p.add_argument('--sed', type=Path, required=True)
p.add_argument('--awk', type=Path, required=True)
a = p.parse_args()
ports = Path(__file__).resolve().parents[2]
helper = ports / 'scripts/stage-local-patch-refresh.py'
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk.host_services import _service_path


with tempfile.TemporaryDirectory(prefix='multi-subst-refresh-') as temporary:
    root = Path(temporary).resolve()

    def setup(case, *, mixed=False):
        base = root / case
        recipe, previous = (base / name / 'cat/demo' for name in ('current', 'previous'))
        work = base / 'work'
        source = work / 'demo-1'
        source.mkdir(parents=True)
        archive = base / 'demo-1.tar.xz'
        files = {'input': b'base @FIRST@\n', 'second': b'base @SECOND@\n',
                 'shared': b'base @FIRST@\n', 'keep': b'keep @FIRST@\n'}
        with tarfile.open(archive, 'w:xz') as tar:
            for name, data in files.items():
                member = tarfile.TarInfo('demo-1/' + name)
                member.size = len(data)
                member.mode = 0o755 if name == 'shared' else 0o644
                tar.addfile(member, io.BytesIO(data))
                (source / name).write_bytes(data.replace(b'base', b'old'))
                (source / name).chmod(member.mode)
        raw = archive.read_bytes()
        archive_info = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(raw).hexdigest()}\n'
                        f'SHA512 ({archive.name}) = {hashlib.sha512(raw).hexdigest()}\n'
                        f'Size ({archive.name}) = {len(raw)} bytes\n')
        values = {'WRKDIR': work, 'WRKSRC': source, 'PATCH': a.patch,
                  'PATCH_ARGS': f'-d {source} -E -p0 --batch --forward -V simple -z .orig',
                  'DISTDIR': base, 'DIST_SUBDIR': '', 'DISTFILES': archive.name,
                  'DISTNAME': 'demo-1', 'PKG_DBDIR': base / 'pkgdb', 'CROSS_DESTDIR': '',
                  'PKGBASE': 'demo', 'PKGNAME': 'demo-1', 'PKGVERSION_NOREV': '1',
                  'PATCHFILES': '', 'PATCHDIR': recipe / 'patches',
                  'DISTINFO_FILE': recipe / 'distinfo', 'EXTRACT_ONLY': archive.name,
                  'EXTRACT_USING': 'bsdtar', 'EXTRACT_SUFX': '.tar.xz',
                  'EXTRACT_CMD': '/selected/bsdtar', 'EXTRACT_ENV': '',
                  'EXTRACT_BEFORE_ARGS': '-xf', 'EXTRACT_AFTER_ARGS': '',
                  'LOCALPATCHES': '', 'META_PACKAGE': '', 'PKG_FAIL_REASON': '',
                  '_COOKIE.configure': work / '.configure_done',
                  'SUBST_CLASSES': 'z-last a-first',
                  'SUBST_STAGE.a-first': 'pre-configure',
                  'SUBST_STAGE.z-last': 'do-configure-pre-hook' if mixed else 'pre-configure',
                  'SUBST_FILES.a-first': 'input shared keep',
                  'SUBST_FILES.z-last': 'input second shared',
                  'SUBST_SED.a-first': "-e 's,@FIRST@,@SECOND@,g'",
                  'SUBST_SED.z-last': "-e 's,@SECOND@,/prefix,g'",
                  'SED': a.sed, 'AWK': a.awk, 'RUN': '@set -e;',
                  'ECHO_SUBST_MSG': 'echo', 'INFO_MSG': 'echo', 'WARNING_MSG': 'echo',
                  'FAIL_MSG': 'false', 'TRUE': 'true', 'ECHO': 'echo'}
        for variable, service in (('CMP', 'cmp'), ('RM', 'rm'), ('CHMOD', 'chmod'),
                                  ('MV', 'mv'), ('TOUCH', 'touch'), ('TR', 'tr')):
            values[variable] = _service_path(service)
        makefile = f'.SHELL: name=ksh path={a.shell}\n'
        makefile += ''.join(f'{key}= {value}\n' for key, value in values.items())
        makefile += ('PKGSRCDIR= ${.CURDIR}/../..\n'
                     '.include "${.PARSEDIR}/../../mk/bsd.prefs.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/patch/patch.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/extract/extract.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/subst.mk"\n'
                     'show-vars:\n.for name in ${VARNAMES}\n'
                     '\t@printf "%s\\n" ${${name}:Q}\n.endfor\n'
                     'pre-patch post-patch pre-extract post-extract:\n'
                     f'configure-clean:\n\t@printf done > {base / "clean"}\n')
        for directory, replacement in ((previous, b'old'), (recipe, b'new')):
            (directory / 'patches').mkdir(parents=True)
            (directory / 'Makefile').write_text(makefile)
            patch = b''
            for name in ('input', 'second', 'shared'):
                data = files[name]
                patch += (f'--- {name}\n+++ {name}\n@@ -1 +1 @@\n'.encode() +
                          b'-' + data + b'+' + data.replace(b'base', replacement))
            (directory / 'patches/patch-a').write_bytes(patch)
            (directory / 'distinfo').write_text(
                archive_info + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n')
            for name, contents in {'mk/bsd.prefs.mk': b'# preferences\n',
                                   'mk/patch/patch.mk': b'do-patch:\n\t@true\n',
                                   'mk/extract/extract.mk': b'do-extract:\n\t@true\n'}.items():
                path = directory.parents[1] / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            for name in ('mk/subst.mk', 'mk/scripts/subst-identity.awk'):
                path = directory.parents[1] / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ports / 'upstream/pkgsrc' / name, path)
        # Produce live substitutions/cookies with the actual pkgsrc provider.
        for stage in ('pre-configure', 'do-configure-pre-hook') if mixed else ('pre-configure',):
            subprocess.run([str(a.bmake), '-C', str(previous), stage], check=True,
                           capture_output=True, text=True)
        (source / 'shared').chmod(0o751)
        (source / 'second').chmod(0o640)
        (source / 'object.o').write_bytes(b'compatible object\n')
        (work / '.patch_done').write_text(str(recipe / 'patches/patch-a') + '\n')
        owner = base / 'pkgdb/demo-1/+BUILD_VERSION'
        owner.parent.mkdir(parents=True)
        owner.write_text(''.join(f'cat/demo/{name}: {hashlib.sha256((previous / name).read_bytes()).hexdigest()}\n'
                                 for name in ('Makefile', 'patches/patch-a')))
        command = [sys.executable, '-B', str(helper), '--sdk-source', str(a.sdk_source),
                   '--bmake', str(a.bmake), '--native', '--recipe', str(recipe),
                   '--expected-work', str(work), '--previous-recipe', str(previous)]
        return base, work, source, command

    def snapshot(work):
        return {p.relative_to(work): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
                for p in work.rglob('*') if p.is_file()}

    selection = ['--refresh-subst', 'z-last', '--refresh-subst', 'a-first']
    base, work, source, command = setup('ordered')
    before = snapshot(work)
    result = subprocess.run(command + selection, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    after = snapshot(work)
    for name in ('input', 'second', 'shared'):
        path = source / name
        assert path.read_bytes() == b'new /prefix\n', path
        assert path.stat().st_mode == before[path.relative_to(work)][2]
    for name in ('demo-1/object.o', 'demo-1/keep', '.subst_a-first_done', '.subst_z-last_done'):
        assert after[Path(name)] == before[Path(name)], name
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    assert (base / 'clean').is_file()

    for case, marker in [('unselected', 'changed source needs substitution refresh'),
                         ('foreign-second', 'live preimage differs: second'),
                         ('foreign-keep', 'unchanged existing SUBST input differs: keep'),
                         ('second-cookie', 'existing SUBST cookie differs from replay: z-last'),
                         ('mixed', 'existing SUBST classes use different stages'),
                         ('duplicate', 'duplicate existing SUBST class')]:
        base, work, source, command = setup(case, mixed=case == 'mixed')
        selected = selection
        if case == 'unselected':
            selected = ['--refresh-subst', 'a-first']
        elif case.startswith('foreign-'):
            (source / case.removeprefix('foreign-')).write_bytes(b'unexpected edit\n')
        elif case == 'second-cookie':
            (work / '.subst_z-last_done').write_text('foreign\n')
        elif case == 'duplicate':
            selected = selection + ['--refresh-subst', 'a-first']
        before = snapshot(work)
        result = subprocess.run(command + selected, capture_output=True, text=True)
        assert result.returncode and marker in result.stderr, (case, result.stderr)
        assert snapshot(work) == before, case
        assert not (base / 'clean').exists(), case

    # Exercise the actual controller's argv construction, not a second parser.
    controller = (ports / 'scripts/cross-bulk.sh').read_text()
    start = controller.index('        if [ -n "${CROSS_BULK_PATCH_REFRESH_EXISTING_SUBST:-}" ]; then')
    end = controller.index('\n        if ', start + 1)
    script = 'set -- sentinel\n' + controller[start:end] + '\nprintf "%s\\n" "$@"\n'
    env = dict(os.environ, CROSS_BULK_PATCH_REFRESH_EXISTING_SUBST='z-last a-first')
    result = subprocess.run([str(a.shell), '-c', script], env=env,
                            capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == ['sentinel', *selection], result.stdout

print('PASS: multiple real SUBST classes, lexical replay, per-class cookies, modes/mtimes and refusals')
