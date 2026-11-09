#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Replay completed GNU configure hooks with real bmake and unchanged SUBST/interpreters."""
import argparse
import difflib
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


with tempfile.TemporaryDirectory(prefix='gnu-refresh-') as temporary:
    root = Path(temporary).resolve()

    def setup(case, *, configured=True, gnu=True):
        base = root / case
        recipe, previous = (base / name / 'cat/demo' for name in ('current', 'previous'))
        work = base / 'work'
        source = work / 'demo-1'
        source.mkdir(parents=True)
        archive = base / 'demo-1.tar.xz'
        files = {'configure': b'#!/usr/bin/env sh\n# base\n# OS_PREP\ncase x in\n @FIRST@ | --recheck)\n  true ;;\nesac\n',
                 'keep': b'keep @FIRST@\n'}
        with tarfile.open(archive, 'w:xz') as tar:
            for name, data in files.items():
                member = tarfile.TarInfo('demo-1/' + name)
                member.size = len(data)
                member.mode = 0o755 if name == 'configure' else 0o644
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
                  'SUBST_STAGE.z-last': 'pre-configure',
                  'SUBST_FILES.a-first': 'configure keep',
                  'SUBST_FILES.z-last': 'configure',
                  'SUBST_SED.a-first': "-e 's,@FIRST@,@SECOND@,g'",
                  'SUBST_SED.z-last': "-e 's,@SECOND@,-recheck,g'",
                  'SED': a.sed, 'AWK': a.awk, 'RUN': '@set -e;',
                  'ECHO_SUBST_MSG': 'echo', 'INFO_MSG': 'echo', 'WARNING_MSG': 'echo',
                  'STEP_MSG': 'echo', 'TEST': 'test',
                  'PREFIX': '/prefix', 'PKGPATH': 'cat/demo', 'MACHINE_PLATFORM': 'NetBSD-11.0-aarch64',
                  'CONFIGURE_SCRIPT': './configure', 'OVERRIDE_DIRDEPTH': '2',
                  'REPLACE_INTERPRETER': 'test-sh', 'REPLACE_FILES.test-sh': 'configure',
                  'REPLACE.test-sh.old': '.*sh', 'REPLACE.test-sh.new': '/selected/sh',
                  '_SCRIPT.configure-scripts-osdep': '${SED} s,OS_PREP,OS_DONE, $$file > $$file.osdep; ${CHMOD} +x $$file.osdep; ${MV} $$file.osdep $$file',
                  'FAIL_MSG': 'false', 'TRUE': 'true', 'ECHO': 'echo'}
        for variable, service in (('CMP', 'cmp'), ('RM', 'rm'), ('CHMOD', 'chmod'),
                                  ('EXPR', 'expr'), ('MV', 'mv'), ('TOUCH', 'touch'), ('TR', 'tr')):
            values[variable] = _service_path(service)
        if case == 'explicit':
            values['CONFIGURE_SCRIPTS_OVERRIDE'] = './configure absent/sub/configure'
        if gnu:
            values['GNU_CONFIGURE'] = 'yes'
        makefile = f'.SHELL: name=ksh path={a.shell}\n'
        makefile += ''.join(f'{key}= {value}\n' for key, value in values.items())
        makefile += ('PKGSRCDIR= ${.CURDIR}/../..\n'
                     '.include "${.PARSEDIR}/../../mk/bsd.prefs.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/patch/patch.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/extract/extract.mk"\n'
                     '.if defined(GNU_CONFIGURE)\n'
                     '.include "${.PARSEDIR}/../../mk/configure/gnu-configure.mk"\n.endif\n'
                     '.include "${.PARSEDIR}/../../mk/configure/replace-interpreter.mk"\n'
                     '.include "${.PARSEDIR}/../../mk/subst.mk"\n'
                     'show-vars:\n.for name in ${VARNAMES}\n'
                     '\t@printf "%s\\n" ${${name}:Q}\n.endfor\n'
                     'pre-patch post-patch pre-extract post-extract:\n'
                     f'configure-clean:\n\t@printf done > {base / "clean"}\n')
        for directory, replacement in ((previous, b'old'), (recipe, b'new')):
            (directory / 'patches').mkdir(parents=True)
            (directory / 'Makefile').write_text(makefile)
            patch = b''
            data = files['configure'].decode()
            patch = ''.join(difflib.unified_diff(data.splitlines(True),
                         data.replace('base', replacement.decode()).splitlines(True),
                         fromfile='configure', tofile='configure')).encode()
            (directory / 'patches/patch-a').write_bytes(patch)
            (directory / 'distinfo').write_text(
                archive_info + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n')
            for name, contents in {'mk/bsd.prefs.mk': b'# preferences\n',
                                   'mk/patch/patch.mk': b'do-patch:\n\t@true\n',
                                   'mk/extract/extract.mk': b'do-extract:\n\t@true\n'}.items():
                path = directory.parents[1] / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            for name in ('mk/subst.mk', 'mk/scripts/subst-identity.awk',
                         'mk/configure/gnu-configure.mk', 'mk/configure/replace-interpreter.mk'):
                path = directory.parents[1] / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ports / 'upstream/pkgsrc' / name, path)
            subprocess.run([str(a.patch), '-d', str(directory.parents[1]), '-p1', '-F0',
                            '-i', str(ports / 'profiles/common-build-tools/patches/pkgsrc-gnu-configure-idempotent.patch')],
                           check=True, capture_output=True, text=True)
        # Real owner order: pre-configure SUBST, then GNU and interpreter hooks.
        stages = ['pre-configure'] + (['do-configure-pre-hook'] if configured else [])
        result = subprocess.run([str(a.bmake), '-C', str(previous), *stages],
                                capture_output=True, text=True)
        assert result.returncode == 0, (result.stdout, result.stderr)
        if configured:
            (work / '.configure_done').write_text('configured\n')
        (source / 'configure').chmod(0o751)
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
    for case in ('configured', 'explicit', 'unconfigured', 'non-gnu', 'foreign'):
        base, work, source, command = setup(case, configured=case != 'unconfigured', gnu=case != 'non-gnu')
        if case == 'foreign':
            with (source / 'configure').open('ab') as out:
                out.write(b'# unrelated live edit\n')
        before = snapshot(work)
        result = subprocess.run(command + selection, capture_output=True, text=True)
        if case == 'foreign':
            assert result.returncode and 'live preimage differs: configure' in result.stderr, result.stderr
            assert snapshot(work) == before
            continue
        assert result.returncode == 0, result.stderr
        data = (source / 'configure').read_bytes()
        assert b'# new\n' in data and b'@FIRST@' not in data
        if case in ('configured', 'explicit'):
            assert data.count(b'\t: Avoid regenerating within pkgsrc\n\texit 0\n') == 1, data
            assert b'#!/selected/sh\n' in data and b'# OS_DONE\n' in data, data
            # Repeat the real owner after reconfiguration: no second guard or metadata churn.
            path = source / 'configure'
            stable = (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns, path.stat().st_ino)
            subprocess.run([str(a.bmake), '-C', str(base / 'current/cat/demo'),
                            'configure-scripts-override'], check=True, capture_output=True, text=True)
            assert (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns, path.stat().st_ino) == stable
        else:
            assert b'Avoid regenerating' not in data and b'# OS_PREP\n' in data, data
        after = snapshot(work)
        for name in ('demo-1/object.o', 'demo-1/keep', '.subst_a-first_done', '.subst_z-last_done'):
            assert after[Path(name)] == before[Path(name)], name
        assert not (work / '.emberbsd-patch-refresh.json').exists()

print('PASS: real GNU hooks, idempotent guard, stage order, non-GNU/unconfigured exclusion and live-edit refusal')
