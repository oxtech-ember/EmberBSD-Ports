#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Query the real exported native compiler-rt recipe without building it."""
import argparse
import json
import re
from pathlib import Path
import shlex
import subprocess
import tarfile


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('bmake', 'pkgsrc', 'makeconf', 'sdk', 'libtool', 'distfile', 'patch', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--sdk-version', required=True)
    args = cli.parse_args()
    args.work.mkdir()
    keys = ('PKGNAME', 'PATCHDIR', 'PATCH_WRKSRC', 'PATCH_ARGS', 'PATCH_STRIP', 'PKG_FAIL_REASON',
            'CMAKE_CONFIGURE_ARGS', 'LOCALBASE')

    def query(label, *extra):
        command = [str(args.bmake), '-C', str(args.pkgsrc / 'lang/compiler-rt'),
            'MAKECONF=' + str(args.makeconf), 'OSX_SDK_PATH=' + str(args.sdk),
            'EMBERBSD_DARWIN_SDK_VERSION=' + args.sdk_version,
            'EMBERBSD_DARWIN_LIBTOOL=' + str(args.libtool), *extra,
            *[word for key in keys for word in ('-V', key + '=${' + key + '}')]]
        result = subprocess.run(command, capture_output=True, text=True)
        (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0 and not result.stderr, result.stderr
        rows = dict(line.split('=', 1) for line in result.stdout.splitlines())
        assert set(rows) == set(keys)
        return rows

    native = query('darwin')
    assert native['PKGNAME'] == 'compiler-rt-23.1.4nb1'
    assert native['PATCHDIR'] == str(args.pkgsrc / 'lang/compiler-rt/patches')
    assert native['PATCH_WRKSRC'].endswith('/llvm-project-23.1.4.src')
    assert native['PATCH_STRIP'] == '-p1' and native['PKG_FAIL_REASON'] == ''
    patch_args = shlex.split(native['PATCH_ARGS'])
    assert patch_args[0:2] == ['-d', native['PATCH_WRKSRC']], patch_args
    assert {'--forward', '--quiet', '-E', '-p1'} <= set(patch_args), patch_args
    member_name = 'llvm-project-23.1.4.src/compiler-rt/lib/builtins/comparetf2.c'
    with tarfile.open(args.distfile, 'r:xz') as archive:
        member = archive.extractfile(member_name)
        assert member is not None, member_name
        source = member.read()
    patch_root = args.work / 'patch-root'
    target = patch_root / 'compiler-rt/lib/builtins/comparetf2.c'
    target.parent.mkdir(parents=True)
    target.write_bytes(source)
    fixture_args = list(patch_args)
    fixture_args[1] = str(patch_root)
    patch_file = args.pkgsrc / 'lang/compiler-rt/patches/patch-00-binary128-fenv'
    applied = subprocess.run([str(args.patch), *fixture_args], input=patch_file.read_bytes(),
                             capture_output=True, cwd=args.pkgsrc)
    assert applied.returncode == 0, (applied.stdout + applied.stderr).decode(errors='replace')
    patched = target.read_text()
    assert 'binary128_raise_invalid' in patched and 'COMPILER_RT_NETBSD_AARCH64_FENV' in patched
    assert (target.parent / 'LICENSE.EmberBSD-BINARY128.TXT').is_file()
    options = shlex.split(native['CMAKE_CONFIGURE_ARGS'])
    for value in ('-DDARWIN_macosx_CACHED_SYSROOT=' + str(args.sdk),
                  '-DDARWIN_macosx_OVERRIDE_SDK_VERSION=' + args.sdk_version,
                  '-DLLVM_CMAKE_DIR=' + native['LOCALBASE'],
                  '-DCMAKE_LIPO=' + native['LOCALBASE'] + '/bin/llvm-lipo'):
        assert value in options, value
    for name in ('IOS', 'WATCHOS', 'TVOS', 'XROS'):
        assert '-DCOMPILER_RT_ENABLE_' + name + '=OFF' in options
    for label, extra in (('missing-version', 'EMBERBSD_DARWIN_SDK_VERSION='),
                         ('missing-sdk', 'OSX_SDK_PATH=')):
        assert 'requires explicit OSX_SDK_PATH' in query(label, extra)['PKG_FAIL_REASON']
    # A foreign host cannot use the caller's Darwin bootstrap configuration.
    # Parse the actual recipe conditional alone to check its platform scope.
    lines = (args.pkgsrc / 'lang/compiler-rt/Makefile').read_text().splitlines(True)
    start = lines.index('.if ${OPSYS} == "Darwin"\n')
    selected, depth = [], 0
    for line in lines[start:]:
        selected.append(line)
        if re.match(r'\.\s*if\b', line):
            depth += 1
        elif re.match(r'\.\s*endif\b', line):
            depth -= 1
        if depth == 0:
            break
    fixture = args.work / 'linux.mk'
    fixture.write_text('OPSYS=Linux\n' + ''.join(selected))
    other = subprocess.run([str(args.bmake), '-r', '-f', str(fixture),
        '-V', '${PKG_FAIL_REASON}', '-V', '${CMAKE_CONFIGURE_ARGS}'],
        capture_output=True, text=True, check=True)
    assert other.stdout == '\n\n' and other.stderr == '', other

    (args.work / 'result.json').write_text(json.dumps(dict(status='PASS', cases=5,
        scope='Actual recipe metadata and isolated application of its monorepo patch; no build')) + '\n')
    print('PASS: compiler-rt patch root/arguments apply the actual binary128 patch; Darwin metadata remains selected')


if __name__ == '__main__':
    main()
