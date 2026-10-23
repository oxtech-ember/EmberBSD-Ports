#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted tests of actual pkgsrc builtin fragments.
"""Check direct and generic libedit selection with a real BSD make and pkg_admin."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True, type=Path)
parser.add_argument('--pkg-admin', required=True, type=Path)
parser.add_argument('--pkgsrc', required=True, type=Path)
parser.add_argument('--work-parent', required=True, type=Path)
a = parser.parse_args()
recipe = Path(__file__).resolve().parents[1]
checks = 0
with tempfile.TemporaryDirectory(prefix='editline-builtin-', dir=a.work_parent) as temporary:
    root = Path(temporary)
    tree = root / 'pkgsrc'
    shutil.copytree(recipe, tree / 'devel/editline')
    for relative in ('mk/buildlink3/bsd.builtin.mk', 'mk/buildlink3/find-files.mk',
                     'mk/buildlink3/find-libs.mk', 'mk/buildlink3/find-headers.mk',
                     'mk/buildlink3/find-pkgconfig-files.mk',
                     'mk/readline.builtin.mk', 'mk/readline.buildlink3.mk'):
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.pkgsrc / relative, target)
    (tree / 'mk/bsd.fast.prefs.mk').write_text('')
    (tree / 'mk/termcap.buildlink3.mk').write_text('BUILTIN_LIBNAME.termcap=terminfo\nTERM_PROVIDER=base\n')
    (tree / 'devel/ncurses').mkdir()
    (tree / 'devel/ncurses/buildlink3.mk').write_text('TERM_PROVIDER=package\n')
    consumer = tree / 'tests/consumer'
    consumer.mkdir(parents=True)
    sysroot = root / 'sysroot'
    for name in ('usr/include/readline/readline.h', 'usr/include/histedit.h', 'usr/lib/libedit.so'):
        f = sysroot / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('/* NetBSD fixture */\n')
    marker = sysroot / 'usr/share/emberbsd/ports/editline.distinfo'
    marker.parent.mkdir(parents=True)
    template = f"""OPSYS=NetBSD
LOCALBASE=/usr/pkg
TOOLS_CROSS_DESTDIR={sysroot}
COMPILER_INCLUDE_DIRS=/usr/include
COMPILER_LIB_DIRS=/usr/lib
AWK=awk
GREP=grep
ECHO=echo
TEST=test
PKG_ADMIN={a.pkg_admin}
USE_TOOLS=
PREFER_NATIVE=yes
BUILDLINK_TREE=
PKG_FAIL_REASON=
"""
    def run(name, *, marker_state='match', generic=False, overrides='', expected='yes', fail=False, repeat=False, targets=()):
        global checks
        if marker_state == 'match':
            marker.write_bytes((recipe / 'distinfo').read_bytes())
        elif marker_state == 'stale':
            marker.write_bytes((recipe / 'distinfo').read_bytes().replace(b'SHA1', b'SHA2', 1))
        elif marker.exists():
            marker.unlink()
        include = '../../mk/readline.buildlink3.mk' if generic else '../../devel/editline/buildlink3.mk'
        text = template + overrides + f'\n.include "{include}"\n'
        if repeat or targets:
            text += '.include "../../devel/editline/builtin.mk"\n'
        text += f'BUILDLINK_DIR={root}/build link\nBUILDLINK_PREFIX.editline=/usr\nMKDIR=mkdir -p\nLN=ln\nBASENAME=basename\nDIRNAME=dirname\nECHO_BUILDLINK_MSG=echo\n'
        text += 'all:\n\t@echo "use=${USE_BUILTIN.editline}"\n\t@echo fail=${PKG_FAIL_REASON:Q}\n\t@echo "version=${BUILTIN_PKG.editline:U}"\n\t@echo "term=${TERM_PROVIDER:U}"\n'
        (consumer / 'Makefile').write_text(text)
        done = subprocess.run([str(a.bmake), '-r', '-f', 'Makefile', 'all', *targets], cwd=consumer, text=True, capture_output=True, timeout=30)
        if done.returncode:
            raise AssertionError(f'{name}: {done.stderr}')
        values = dict(line.split('=', 1) for line in done.stdout.splitlines() if line.startswith(('use=', 'fail=', 'version=', 'term=')))
        assert values['use'] == expected, (name, values)
        assert bool(values['fail']) == fail, (name, values)
        if expected == 'yes' and not fail:
            assert values['version'] == 'editline-3.1.20260512', (name, values)
            assert values['term'] == 'base', (name, values)
        checks += 1
    for generic in (False, True):
        suffix = 'generic' if generic else 'direct'
        run('accepted-' + suffix, generic=generic)
        run('repeated-' + suffix, generic=generic, repeat=True)
        run('unmarked-external-' + suffix, generic=generic, marker_state='missing', expected='no')
        run('unmarked-emberbsd-' + suffix, generic=generic, marker_state='missing', overrides='EMBERBSD_PORTS=yes\n', expected='no', fail=True)
        run('changed-patch-' + suffix, generic=generic, marker_state='stale', expected='no', fail=True)
        run('preset-detection-' + suffix, generic=generic, marker_state='missing', overrides='IS_BUILTIN.editline=yes\n', expected='no')
        run('forced-invalid-' + suffix, generic=generic, marker_state='missing', overrides='USE_BUILTIN.editline=yes\n', expected='yes', fail=True)
        run('second-provider-' + suffix, generic=generic, overrides='PREFER.editline=pkgsrc\n', expected='no', fail=True)
        run('too-new-api-' + suffix, generic=generic, overrides='BUILDLINK_API_DEPENDS.editline=editline>=99\n', expected='no', fail=True)
        run('wrong-cross-root-' + suffix, generic=generic, overrides=f'TOOLS_CROSS_DESTDIR={root}/absent\n_CROSS_DESTDIR={sysroot}\nREADLINE_DEFAULT=editline\nEMBERBSD_PORTS=yes\n', expected='no', fail=True)
        for missing in ('usr/include/histedit.h', 'usr/lib/libedit.so'):
            item = sysroot / missing
            saved = item.read_bytes()
            item.unlink()
            run('missing-' + missing + '-' + suffix, generic=generic, overrides='READLINE_DEFAULT=editline\n', expected='no', fail=True)
            item.write_bytes(saved)
    (tree / 'EMBERBSD-PKGSRC-REVISION').write_text('fixture\n')
    for generic in (False, True):
        run('exported-unmarked', generic=generic, marker_state='missing', expected='no', fail=True)
        run('exported-qualified', generic=generic)
    (tree / 'EMBERBSD-PKGSRC-REVISION').unlink()
    headers = sysroot / 'usr/include/editline/readline.h'
    headers.parent.mkdir(parents=True)
    headers.write_text('/* NetBSD compatibility header */\n')
    link = root / 'build link'
    targets = ('ensure-libedit-pc', 'buildlink-readline-readline-h', 'buildlink-readline-history-h')
    run('created-buildlink-files', targets=targets)
    assert 'Version: 3.1.20260512' in (link / 'lib/pkgconfig/libedit.pc').read_text()
    for name in ('history.h', 'readline.h'):
        assert (link / 'include/readline' / name).resolve() == headers
    shutil.rmtree(link)
    pc = sysroot / 'usr/lib/pkgconfig/libedit.pc'
    pc.parent.mkdir(parents=True)
    pc.write_text('Name: base libedit\nVersion: 3.1.20260512\n')
    run('existing-base-pkgconfig', targets=('ensure-libedit-pc',))
    assert (link / 'lib/pkgconfig/libedit.pc').resolve() == pc
print(f'PASS: {checks} actual BSD make libedit provider cases')
