#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate QtBase split identities with bmake; no compilation or pkgdb writes."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--work-parent', type=Path, required=True)
args = parser.parse_args()
if not args.bmake.is_absolute() or not args.bmake.is_file():
    parser.error('select an absolute bmake executable')
if not args.work_parent.is_absolute() or not args.work_parent.is_dir():
    parser.error('select an existing absolute work parent')
root = Path(__file__).resolve().parents[1]
fields = ('PKGNAME', 'PKGREVISION', 'DEPENDS', 'PKG_FAIL_REASON')

with tempfile.TemporaryDirectory(prefix='qt-package-revisions-', dir=args.work_parent) as directory:
    work = Path(directory)
    recipe = work / 'Makefile'
    revisions = work / 'package-revisions.mk'
    original = (root / 'Makefile').read_text()
    # Stub pkgsrc infrastructure, retaining the actual recipe's revision include
    # and all of its role/target/refusal conditions. The wrapper selects devel.
    source = re.sub(r'^\.\s*include "([^"]+)".*$',
                    lambda m: m[0] if m[1] == 'package-revisions.mk' else '',
                    original, flags=re.M)
    recipe.write_text(source)
    if (root / revisions.name).exists():
        revisions.write_bytes((root / revisions.name).read_bytes())
    wrapper = re.sub(r'^\.\s*include "([^"]+)".*$',
                     lambda m: '.include "' + str(recipe) + '"'
                     if m[1].endswith('/Makefile') else '',
                     (root.parent / 'qt6-qtbase-devel/Makefile').read_text(), flags=re.M)
    (work / 'devel.mk').write_text(wrapper)

    def evaluate(*, devel=False, cross=True, arch='aarch64', override=None):
        command = [str(args.bmake), '-r', '-m', '/', '-f', str(work / 'devel.mk' if devel else recipe),
                   'QTVERSION=6.12.0', 'OPSYS=NetBSD' if cross else 'OPSYS=Darwin',
                   'USE_CROSS_COMPILE=yes' if cross else 'USE_CROSS_COMPILE=no',
                   'MACHINE_ARCH=' + arch, 'PKGPATH=x11/qt6-qtbase' + ('-devel' if devel else ''),
                   'WRKDIR=' + str(work / 'objects'), 'QTPREFIX=/usr/pkg/qt6',
                   'PKGSRC_COMPILER=clang', 'PLATFORM_SUPPORTS_WAYLAND=no']
        if override is not None:
            command.append('PKGREVISION=' + str(override))
        for field in fields:
            command += ['-V', '${' + field + '}']
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, check=True)
        values = result.stdout.splitlines()
        if len(values) != len(fields):
            raise AssertionError('unexpected bmake metadata: ' + result.stdout + result.stderr)
        return dict(zip(fields, values))

    runtime, devel, native = evaluate(), evaluate(devel=True), evaluate(cross=False)
    for arch in ('aarch64', 'x86_64'):
        pair = evaluate(devel=True, arch=arch)
        assert not pair['PKG_FAIL_REASON'], pair
        assert runtime['PKGNAME'] + 'nb' + runtime['PKGREVISION'] + ':../../x11/qt6-qtbase' in pair['DEPENDS'].split(), pair
        assert pair['PKGREVISION'] == devel['PKGREVISION'], pair
    assert not runtime['PKG_FAIL_REASON'] and not native['PKG_FAIL_REASON']
    assert evaluate(devel=True, cross=False)['PKG_FAIL_REASON']
    assert evaluate(arch='earmv7hf')['PKG_FAIL_REASON']
    assert evaluate(override=int(runtime['PKGREVISION']) + 1)['PKG_FAIL_REASON']
    assert evaluate(devel=True, override=int(devel['PKGREVISION']) + 1)['PKG_FAIL_REASON']

    # Change one declaration, as a future maintainer would. Dependencies and
    # refusal checks must follow it. The devel identity remains independent;
    # publishing changed devel dependency metadata still requires its own bump.
    changed = str(int(runtime['PKGREVISION']) + 1)
    declaration = revisions if revisions.exists() else recipe
    variable = 'QTBASE_RUNTIME_REVISION' if revisions.exists() else 'PKGREVISION'
    data, count = re.subn(r'^' + variable + r'=[ \t]*' + runtime['PKGREVISION'] + r'[ \t]*$',
                         variable + '= ' + changed, declaration.read_text(), count=1, flags=re.M)
    assert count == 1, 'runtime revision declaration not found'
    declaration.write_text(data)
    updated_runtime, updated_devel = evaluate(), evaluate(devel=True)
    assert not updated_runtime['PKG_FAIL_REASON'], updated_runtime
    assert not updated_devel['PKG_FAIL_REASON'], updated_devel
    assert updated_runtime['PKGREVISION'] == changed, updated_runtime
    assert updated_runtime['PKGNAME'] + 'nb' + changed + ':../../x11/qt6-qtbase' in updated_devel['DEPENDS'].split(), updated_devel
    assert updated_devel['PKGREVISION'] == devel['PKGREVISION'], updated_devel
    assert evaluate(cross=False) == native, 'cross revision changed the native identity'

print('PASS: QtBase split identities, exact dependency, refusals and a single-source revision change')
