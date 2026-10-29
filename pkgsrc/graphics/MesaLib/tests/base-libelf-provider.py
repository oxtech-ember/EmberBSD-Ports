#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Mesa's base-libelf guard and native/cross bmake selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import sys
import tempfile


RECIPE = Path(__file__).resolve().parents[1]
PORTS = RECIPE.parents[2]
CHECKER = RECIPE / 'files/check-base-libelf.py'
SDK_SELECTOR = PORTS / 'pkgsrc/lang/llvm/files/sdk_source.py'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def make_elf(machine, kind, soname=None):
    ident = b'\x7fELF\x02\x01\x01\x02\x00' + b'\0' * 7
    if soname is None:
        return struct.pack('<16sHHIQQQIHHHHHH', ident, kind, machine, 1, 0,
                           0, 0, 0, 64, 56, 0, 0, 0, 0)
    dynamic_offset = 64 + 2 * 56
    strings_offset = dynamic_offset + 4 * 16
    strings = b'\0' + soname.encode('ascii') + b'\0'
    dynamic = b''.join(struct.pack('<qQ', tag, value) for tag, value in (
        (5, strings_offset), (10, len(strings)), (14, 1), (0, 0)))
    size = strings_offset + len(strings)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, kind, machine, 1, 0,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    load = struct.pack('<IIQQQQQQ', 1, 5, 0, 0, 0, size, size, 4096)
    dynamic_header = struct.pack('<IIQQQQQQ', 2, 4, dynamic_offset,
                                 dynamic_offset, dynamic_offset, len(dynamic),
                                 len(dynamic), 8)
    return header + load + dynamic_header + dynamic + strings


def make_archive(member):
    fields = (b'abi.o/'.ljust(16) + b'0'.ljust(12) + b'0'.ljust(6) +
              b'0'.ljust(6) + b'100644'.ljust(8) + str(len(member)).encode().ljust(10) + b'`\n')
    require(len(fields) == 60, 'fixture archive header is not 60 bytes')
    return b'!<arch>\n' + fields + member + (b'\n' if len(member) % 2 else b'')


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fixture(root, sdk_source):
    pkgsrc = root / 'pkgsrc'
    recipe = pkgsrc / 'devel/elftoolchain'
    (recipe / 'patches').mkdir(parents=True)
    (recipe / 'files').mkdir()
    (recipe / 'Makefile').write_text('# fixture source recipe\n')
    (pkgsrc / 'lang/llvm/files').mkdir(parents=True)
    shutil.copyfile(SDK_SELECTOR, pkgsrc / 'lang/llvm/files/sdk_source.py')

    headers = {
        'libelf/libelf.h': b'typedef struct { uint64_t d_align; void *d_buf; uint64_t d_off; uint64_t d_size; int d_type; unsigned int d_version; } Elf_Data;\n',
        'libelf/gelf.h': b'#include <libelf.h>\ntypedef Elf_Data GElf_Data;\n',
        'common/elfdefinitions.h': b'#include <sys/elfdefinitions.h>\n',
    }
    archive_bytes = b'fixture upstream archive metadata'
    patch_data = b'$NetBSD: patch-example,v 1.1 $\n--- libelf.h.orig\n+++ libelf.h\n@@ -1 +1 @@\n-old\n+new\n'
    write_bytes(recipe / 'patches/patch-example', patch_data)
    patch_hash = hashlib.sha1(b''.join(line for line in patch_data.splitlines(keepends=True)
                                      if b'$NetBSD' not in line)).hexdigest()
    archive = dict(size=len(archive_bytes), sha256=hashlib.sha256(archive_bytes).hexdigest(),
                   sha512=hashlib.sha512(archive_bytes).hexdigest(),
                   blake2s=hashlib.blake2s(archive_bytes).hexdigest())
    metadata = dict(format='emberbsd-elftoolchain-base-source', version=1,
                    upstream=dict(distname='elftoolchain-test', archive=archive),
                    files={name: dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
                           for name, data in headers.items()},
                    packaging_overrides={})
    write_bytes(recipe / 'files/base-source.json', json.dumps(metadata, sort_keys=True).encode())
    distinfo = ('BLAKE2s (elftoolchain-test.tar.bz2) = ' + archive['blake2s'] + '\n' +
                'SHA512 (elftoolchain-test.tar.bz2) = ' + archive['sha512'] + '\n' +
                'Size (elftoolchain-test.tar.bz2) = ' + str(archive['size']) + ' bytes\n' +
                'SHA1 (patch-example) = ' + patch_hash + '\n').encode()
    write_bytes(recipe / 'distinfo', distinfo)

    target = root / 'target'
    write_bytes(target / 'usr/share/emberbsd/ports/elftoolchain.distinfo', distinfo)
    for name, data in headers.items():
        relative = {'libelf/libelf.h': 'usr/include/libelf.h',
                    'libelf/gelf.h': 'usr/include/gelf.h',
                    'common/elfdefinitions.h': 'usr/include/elfdefinitions.h'}[name]
        write_bytes(target / relative, data)
    write_bytes(target / 'usr/include/sys/elfdefinitions.h',
                b'/* Copyright \xc2\xa9 EmberBSD contributors. */\n'
                b'#define ELFCLASS32 1U\n#define ELFCLASS64 2U\n#define ELFDATA2LSB 1U\n'
                b'#define STN_UNDEF 0\n')
    write_bytes(target / 'usr/lib/libelf.so.2.0', make_elf(62, 3, 'libelf.so.2'))
    write_bytes(target / 'usr/lib/libelf.a', make_archive(make_elf(62, 1)))
    (target / 'usr/lib/libelf.so.2').symlink_to('libelf.so.2.0')
    (target / 'usr/lib/libelf.so').symlink_to('libelf.so.2')
    buildlink = root / 'buildlink'
    buildlink.mkdir()
    return dict(recipe=recipe, target=target, buildlink=buildlink,
                sdk_source=sdk_source.resolve(), distinfo=distinfo)


def checker_args(case, *, mode='cross', arch='x86_64', sdk=None, target=None):
    return [sys.executable, '-B', '-E', '-S', str(CHECKER),
            '--base-recipe', str(case['recipe']),
            '--sdk-source', str(sdk or case['sdk_source']),
            '--target-root', str(target or case['target']),
            '--buildlink-dir', str(case['buildlink']),
            '--mode', mode, '--arch', arch]


def invoke(case, **kwargs):
    return subprocess.run(checker_args(case, **kwargs), capture_output=True, text=True,
                          timeout=30, env=dict(os.environ, LC_ALL='C'))


def check_fixture(work, sdk_source):
    checks = 0

    def new_case(name):
        return fixture(work / name, sdk_source)

    good = new_case('cross-good')
    result = invoke(good)
    require(result.returncode == 0 and 'PASS:' in result.stdout,
            'actual checker rejected a valid cross provider: ' + result.stderr)
    checks += 1

    cases = []
    case = new_case('wrong-marker')
    marker = case['target'] / 'usr/share/emberbsd/ports/elftoolchain.distinfo'
    marker.write_bytes(marker.read_bytes() + b'# mismatch\n')
    cases.append(('marker mismatch', case, 'marker differs'))

    case = new_case('wrong-patch-checksum')
    with (case['recipe'] / 'patches/patch-example').open('ab') as output:
        output.write(b'changed patch\n')
    cases.append(('patch checksum mismatch', case, 'canonical patch checksum mismatch'))

    case = new_case('wrong-header')
    with (case['target'] / 'usr/include/libelf.h').open('ab') as output:
        output.write(b'/* changed ABI */\n')
    cases.append(('header mismatch', case, 'target header differs'))

    case = new_case('wrong-elf-definitions')
    write_bytes(case['target'] / 'usr/include/sys/elfdefinitions.h',
                b'/* Copyright \xc2\xa9 EmberBSD contributors. */\n'
                b'#define ELFCLASS32 2U\n#define ELFCLASS64 2U\n#define ELFDATA2LSB 1U\n')
    cases.append(('wrong ELF definitions', case,
                  'target ELF definitions have the wrong ELFCLASS32'))

    for label, definition in (('missing-stn-undef', b''),
                              ('wrong-stn-undef', b'#define STN_UNDEF 1\n'),
                              ('conflicting-stn-undef', b'#define STN_UNDEF 0\n#define STN_UNDEF 1\n'),
                              ('expression-stn-undef', b'#define STN_UNDEF 0+1\n')):
        case = new_case(label)
        header = case['target'] / 'usr/include/sys/elfdefinitions.h'
        header.write_bytes(header.read_bytes().replace(b'#define STN_UNDEF 0\n',
                                                       definition))
        cases.append((label, case, 'target ELF definitions have the wrong STN_UNDEF'))

    case = new_case('wrong-soname')
    write_bytes(case['target'] / 'usr/lib/libelf.so.2.0', make_elf(62, 3, 'wrong.so'))
    cases.append(('SONAME mismatch', case, 'wrong ELF class, type, endian, or SONAME'))

    case = new_case('wrong-machine')
    write_bytes(case['target'] / 'usr/lib/libelf.so.2.0', make_elf(183, 3, 'libelf.so.2'))
    cases.append(('ELF machine mismatch', case, 'expected ELF64 little-endian target header'))

    case = new_case('wrong-archive-machine')
    write_bytes(case['target'] / 'usr/lib/libelf.a', make_archive(make_elf(183, 1)))
    cases.append(('archive machine mismatch', case, 'expected ELF64 little-endian target header'))

    case = new_case('wrong-alias')
    alias = case['target'] / 'usr/lib/libelf.so'
    alias.unlink()
    alias.symlink_to('libelf.so.2.0')
    (case['target'] / 'usr/lib/libelf.so.2').unlink()
    write_bytes(case['target'] / 'usr/lib/libother.so', b'wrong provider')
    (case['target'] / 'usr/lib/libelf.so.2').symlink_to('libother.so')
    cases.append(('alias mismatch', case, 'alias does not resolve'))

    case = new_case('buildlink-provider')
    write_bytes(case['buildlink'] / 'include/libelf.h', b'package header\n')
    cases.append(('package provider', case, 'package buildlink supplies libelf'))

    case = new_case('missing-shared-library')
    (case['target'] / 'usr/lib/libelf.so.2.0').unlink()
    cases.append(('missing shared library', case, 'missing target file'))

    bad_sdk = work / 'bad-sdk'
    write_bytes(bad_sdk / 'src/emberbsd_sdk/__init__.py', b'API_VERSION = 2\n')
    bad = new_case('bad-sdk-api')
    cases.append(('unsupported SDK API', bad, 'API version 1'))

    for label, case, expected in cases:
        result = invoke(case, sdk=bad_sdk if label == 'unsupported SDK API' else None)
        require(result.returncode == 1 and expected in result.stderr,
                f'{label}: checker did not reject with its specific contract; '
                f'rc={result.returncode}, stderr={result.stderr!r}')
        checks += 1

    cross_root = invoke(good, mode='cross', target=Path('/'))
    require(cross_root.returncode == 1 and 'never host root /' in cross_root.stderr,
            'cross mode accepted host root /')
    checks += 1
    native_fixture = invoke(good, mode='native')
    require(native_fixture.returncode == 1 and 'native mode must select the host target root /' in native_fixture.stderr,
            'native mode accepted an alternate root')
    checks += 1
    print(f'PASS: {checks} actual-checker cases, including {len(cases)} negative controls')
    return checks


def make_query(bmake, work, source, arch, cross, root):
    work.mkdir(parents=True, exist_ok=True)
    lines = []
    for line in source.splitlines():
        if line.startswith('.include '):
            lines.append('TEST_INCLUDES+= ' + line.split('"')[1])
        else:
            lines.append(line)
    recipe_file = work / 'recipe.mk'
    recipe_file.write_text('\n'.join(lines) + '\n')
    recipe_dir = RECIPE
    fixture_file = work / 'query.mk'
    sdk = work / 'selected-sdk'
    buildlink = work / 'buildlink-query'
    sdk.mkdir(exist_ok=True)
    buildlink.mkdir(exist_ok=True)
    fields = ('PKGREVISION', 'PKG_FAIL_REASON', '_EMBERBSD_MESA_LIBELF_MODE',
              '_EMBERBSD_MESA_LIBELF_ROOT', '_EMBERBSD_MESA_LIBELF_CHECK')
    fixture_file.write_text(f'''OPSYS=NetBSD
OS_VERSION=11.0
MACHINE_ARCH={arch}
USE_CROSS_COMPILE={'yes' if cross else 'no'}
EMBERBSD_COMMON_GRAPHICS=yes
EMBERBSD_SDK_SOURCE={sdk}
TOOL_PYTHONBIN=/selected/python3.15
FILESDIR={RECIPE / 'files'}
BUILDLINK_DIR={buildlink}
CROSS_DESTDIR={root}
PREFIX=/usr/pkg
TOOLBASE=/usr/pkg
PYPKGPREFIX=py315
PYVERSSUFFIX=3.15
.include "{recipe_file}"
show:
.for field in {' '.join(fields)}
\t@printf '%s\\n' ${{${{field}}:Q}}
.endfor
''')
    result = subprocess.run([str(bmake), '-r', '-m', '/', '-f', str(fixture_file), 'show'],
                            cwd=recipe_dir, capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, 'bmake failed: ' + result.stdout + result.stderr)
    values = result.stdout.splitlines()
    require(len(values) == len(fields), 'bmake returned incomplete provider metadata')
    return dict(zip(fields, values)), sdk, buildlink


def check_make_modes(bmake, work):
    source = (RECIPE / 'Makefile').read_text()
    native, sdk, buildlink = make_query(bmake, work / 'native', source, 'x86_64', False, '')
    require(native['PKGREVISION'] == '10' and native['_EMBERBSD_MESA_LIBELF_MODE'] == 'native' and
            native['_EMBERBSD_MESA_LIBELF_ROOT'] == '/', 'native bmake root selection changed')
    argv = shlex.split(native['_EMBERBSD_MESA_LIBELF_CHECK'])
    require(argv[1:4] == ['-B', '-E', '-S'] and '--target-root' in argv and argv[argv.index('--target-root') + 1] == '/' and
            argv[argv.index('--mode') + 1] == 'native' and
            argv[argv.index('--base-recipe') + 1] == str(PORTS / 'pkgsrc/devel/elftoolchain') and
            argv[argv.index('--sdk-source') + 1] == str(sdk) and
            argv[argv.index('--buildlink-dir') + 1] == str(buildlink),
            'native checker argv lost an explicit input')

    cross_root = work / 'cross-sysroot'
    cross_root.mkdir()
    cross, cross_sdk, cross_buildlink = make_query(bmake, work / 'cross', source,
                                                    'x86_64', True, str(cross_root))
    require(cross['_EMBERBSD_MESA_LIBELF_MODE'] == 'cross' and
            cross['_EMBERBSD_MESA_LIBELF_ROOT'] == str(cross_root),
            'cross bmake did not select CROSS_DESTDIR')
    argv = shlex.split(cross['_EMBERBSD_MESA_LIBELF_CHECK'])
    require(argv[argv.index('--target-root') + 1] == str(cross_root) and
            argv[argv.index('--mode') + 1] == 'cross' and
            argv[argv.index('--sdk-source') + 1] == str(cross_sdk) and
            argv[argv.index('--buildlink-dir') + 1] == str(cross_buildlink),
            'cross checker argv lost an explicit input')

    root_fallback, _, _ = make_query(bmake, work / 'cross-host-root', source,
                                     'x86_64', True, '/')
    argv = shlex.split(root_fallback['_EMBERBSD_MESA_LIBELF_CHECK'])
    require(argv[argv.index('--target-root') + 1] == '/' and
            argv[argv.index('--mode') + 1] == 'cross',
            'cross checker stopped receiving the explicit host-root negative control')

    arm, _, _ = make_query(bmake, work / 'aarch64', source, 'aarch64', False, '')
    require(not arm['_EMBERBSD_MESA_LIBELF_CHECK'], 'AArch64 Mesa unexpectedly requires RadeonSI base libelf')

    print('PASS: 4 real bmake native/cross provider-selection queries')
    return 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--work-parent', required=True, type=Path)
    args = parser.parse_args()
    require(args.bmake.is_absolute() and args.bmake.is_file(), '--bmake must be an absolute executable')
    require(args.sdk_source.is_absolute() and args.sdk_source.is_dir(), '--sdk-source must be an absolute directory')
    require(args.work_parent.is_absolute() and args.work_parent.is_dir(), '--work-parent must already exist')
    require(CHECKER.is_file() and SDK_SELECTOR.is_file(), 'Mesa checker or shared SDK selector is missing')
    before = subprocess.check_output(['df', '-k', str(args.work_parent)], text=True)
    work = Path(tempfile.mkdtemp(prefix='mesa-base-libelf-', dir=args.work_parent))
    try:
        checks = check_fixture(work / 'checker-cases', args.sdk_source)
        checks += check_make_modes(args.bmake.resolve(), work / 'bmake-cases')
        after_tests = subprocess.check_output(['df', '-k', str(args.work_parent)], text=True)
        print(f'PASS: {checks} total provider guards and source-selection checks')
        print(before + after_tests, end='')
    finally:
        shutil.rmtree(work)
        require(not work.exists(), 'owned provider test fixture remains')
        after = subprocess.check_output(['df', '-k', str(args.work_parent)], text=True)
        print(after, end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)
