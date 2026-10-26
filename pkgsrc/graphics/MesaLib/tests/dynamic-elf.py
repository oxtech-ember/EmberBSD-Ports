#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the actual Mesa ELF gate with raw bytes and source recipe hooks."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
RECIPE = Path(__file__).resolve().parents[1]
CHECKER = RECIPE / 'files/check-dynamic-elf.py'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def elf_bytes(machine=62, kind=3, tables=(), tags=()):
    """Construct raw ELF64LE table bytes; no target compiler or ELF parser."""
    base, dynamic_offset = 0x400000, 176
    strings = b'\0libfixture.so.1\0'
    count = 4 + 3 * len(tables) + len(tags)
    strings_offset = dynamic_offset + count * 16
    cursor = (strings_offset + len(strings) + 7) & ~7
    dynamic = [(5, base + strings_offset), (10, len(strings)), (14, 1)]
    payload = bytearray(cursor - strings_offset - len(strings))
    for name, types in tables:
        encoding = 'REL' if name == 'REL' else 'RELA'
        size = 16 if encoding == 'REL' else 24
        records = b''.join(struct.pack('<QQ', base + 0x600, value) +
                           (b'' if size == 16 else struct.pack('<q', 0)) for value in types)
        if name == 'JMPREL':
            dynamic += [(23, base + cursor), (2, len(records)), (20, 7)]
        else:
            address_tag, size_tag, entry_tag = (17, 18, 19) if name == 'REL' else (7, 8, 9)
            dynamic += [(address_tag, base + cursor), (size_tag, len(records)), (entry_tag, size)]
        payload.extend(records)
        cursor += len(records)
    dynamic += list(tags) + [(0, 0)]
    dynamic_bytes = b''.join(struct.pack('<qQ', tag, value) for tag, value in dynamic)
    require(len(dynamic_bytes) == count * 16, 'Fixture dynamic layout mismatch')
    size = max(cursor, 2048)
    ident = b'\x7fELF\x02\x01\x01\x02' + bytes(8)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, kind, machine, 1, 0,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    load = struct.pack('<IIQQQQQQ', 1, 6, 0, base, base, size, size, 4096)
    phdr = struct.pack('<IIQQQQQQ', 2, 6, dynamic_offset, base + dynamic_offset,
                       base + dynamic_offset, len(dynamic_bytes), len(dynamic_bytes), 8)
    result = header + load + phdr + dynamic_bytes + strings + payload
    return result + bytes(size - len(result))


def invoke(sdk, arch, *, library=None, checker=CHECKER):
    command = [sys.executable, '-B', '-E', '-S', str(checker), '--sdk-source', str(sdk), '--arch', arch]
    command += ['--library-dir', str(library)] if library is not None else ['--check-sdk']
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def check_bytes(work, sdk):
    checks = 0

    def case(name, data, *, arch='x86_64', valid=True, error=''):
        nonlocal checks
        library = work / name / 'lib'
        library.mkdir(parents=True)
        if data is not None:
            (library / 'libfixture.so.1').write_bytes(data)
        result = invoke(sdk, arch, library=library)
        require((result.returncode == 0) == valid and (not error or error in result.stderr),
                name + ': ' + result.stdout + result.stderr)
        checks += 1
        print('PASS: ' + name)
        return library, result

    old = elf_bytes(tables=(('REL', [8]), ('RELA', [16, 17, 18]), ('JMPREL', [7])))
    good, result = case('old-TLS', old)
    report = json.loads(result.stdout)
    record = report['libraries'][0]
    require(record['sha256'] == hashlib.sha256(old).hexdigest() and
            record['relocations']['count'] == 5 and record['relocations']['types'] == [7, 8, 16, 17, 18],
            'Receipt does not describe the actual compatible bytes')
    bad = None
    for name in ('REL', 'RELA', 'JMPREL'):
        for value in (34, 35, 36):
            bad, _ = case(name + '-TLSDESC-' + str(value), elf_bytes(tables=((name, [value]),)),
                          valid=False, error='unsupported NetBSD x86_64 TLSDESC')
    for tag in (0x6FFFFEF6, 0x6FFFFEF7):
        case('TLSDESC-tag-' + str(tag), elf_bytes(tags=((tag, 0),)), valid=False, error='TLSDESC')
    case('AArch64-policy', elf_bytes(machine=183, tables=(('RELA', [1031]),)), arch='aarch64')
    case('AArch64-policy-isolation', elf_bytes(machine=183, tables=(('RELA', [34, 35, 36, 1031]),),
         tags=((0x6FFFFEF6, 0), (0x6FFFFEF7, 0))), arch='aarch64')
    case('no-ELF', None, valid=False, error='no regular ELF')
    case('CPU-mismatch', elf_bytes(machine=183), valid=False)
    case('wrong-ELF-type', elf_bytes(kind=2), valid=False, error='shared object')
    case('malformed-ELF', b'\x7fELF\x02\x01', valid=False)
    corrupt, _ = case('bad-magic-DSO', b'not ELF', valid=False, error='non-ELF staged DSO')
    (corrupt / 'other.so').write_bytes(old)
    result = invoke(sdk, 'x86_64', library=corrupt)
    require(result.returncode != 0 and 'non-ELF staged DSO' in result.stderr,
            'A damaged DSO disappeared from coverage beside a valid ELF')
    checks += 1

    (good / 'alias.so').symlink_to('libfixture.so.1')
    (good / 'outside-file.so').symlink_to(bad / 'libfixture.so.1')
    (good / 'inside-directory').symlink_to(good, target_is_directory=True)
    result = invoke(sdk, 'x86_64', library=good)
    require(result.returncode == 0 and len(json.loads(result.stdout)['libraries']) == 1,
            'Symlink aliases were followed or scanned twice')
    checks += 1
    root_alias = work / 'root-alias'
    root_alias.symlink_to(good, target_is_directory=True)
    result = invoke(sdk, 'x86_64', library=root_alias)
    require(result.returncode != 0 and 'real directory' in result.stderr, 'Symlink root was accepted')
    checks += 1
    (good / 'escaped-directory').symlink_to(bad, target_is_directory=True)
    result = invoke(sdk, 'x86_64', library=good)
    require(result.returncode != 0 and 'directory symlink escapes' in result.stderr,
            'Directory escape was followed or silently accepted')
    (good / 'escaped-directory').unlink()
    checks += 1

    unsupported = work / 'unsupported-sdk/src/emberbsd_sdk'
    unsupported.mkdir(parents=True)
    (unsupported / '__init__.py').write_text('API_VERSION=1\n')
    (unsupported / 'elf.py').write_text('# Missing relocation capability.\n')
    (unsupported / 'paths.py').write_text('# Missing path capability.\n')
    result = invoke(unsupported.parents[1], 'aarch64')
    require(result.returncode != 0 and 'ELF_RELOCATIONS_API=1' in result.stderr,
            'Pre-configure mode accepted missing SDK capabilities')
    require(invoke(sdk, 'aarch64').returncode == 0, 'SDK capability selection failed')
    checks += 2

    # Change only the actual checker's forbidden-relocation policy, not bytes.
    fixture_pkgsrc = work / 'causal/pkgsrc'
    files = fixture_pkgsrc / 'graphics/MesaLib/files'
    files.mkdir(parents=True)
    selector = fixture_pkgsrc / 'lang/llvm/files/sdk_source.py'
    selector.parent.mkdir(parents=True)
    shutil.copyfile(RECIPE.parents[1] / 'lang/llvm/files/sdk_source.py', selector)
    body = CHECKER.read_text()
    require(body.count('X86_TLSDESC = {34, 35, 36}') == 1, 'Causal policy input changed')
    weakened = files / CHECKER.name
    weakened.write_text(body.replace('X86_TLSDESC = {34, 35, 36}', 'X86_TLSDESC = set()'))
    require(invoke(sdk, 'x86_64', library=bad, checker=weakened).returncode == 0,
            'Removing the policy did not admit the same forbidden fixture')
    checks += 1

    # The SDK readers each protect their own read. The caller must also protect
    # the full dynamic/relocation/hash sequence against an intervening mutation.
    spec = importlib.util.spec_from_file_location('_mesa_elf_gate_test', CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    api, paths = module.load_elf_api(sdk)
    original_reader = api.read_elf_relocations

    def changed_after_scan(path, **kwargs):
        scan = original_reader(path, **kwargs)
        path.write_bytes(path.read_bytes() + b'changed')
        return scan

    api.read_elf_relocations = changed_after_scan
    try:
        try:
            module.inspect_libraries(good, 'x86_64', api, paths)
        except Exception as error:
            require('changed during inspection' in str(error), 'Wrong stability refusal: ' + str(error))
        else:
            raise ValueError('Receipt accepted bytes changed after relocation parsing')
    finally:
        api.read_elf_relocations = original_reader
    checks += 1
    print('PASS: ' + str(checks) + ' actual-checker byte/path/capability/causal cases')


def check_recipe(work, bmake):
    work.mkdir()
    source = (RECIPE / 'Makefile').read_text()
    body = '\n'.join(line for line in source.splitlines() if not line.startswith('.include '))
    cases = 0
    for arch in ('x86_64', 'aarch64'):
        for cross in ('no', 'yes'):
            fixture = work / 'recipe.mk'
            fixture.write_text(f'''OPSYS=NetBSD
MACHINE_ARCH={arch}
USE_CROSS_COMPILE={cross}
EMBERBSD_COMMON_GRAPHICS=yes
EMBERBSD_SDK_SOURCE=/selected/sdk
CROSS_DESTDIR={work}
TOOL_PYTHONBIN=/selected/python3.15
FILESDIR={RECIPE / 'files'}
DESTDIR=/selected/stage
PREFIX=/usr/pkg
TOOLBASE=/usr/pkg
PYVERSSUFFIX=3.15
PYPKGPREFIX=py315
TEST=test
{body}
''')
            result = subprocess.run([str(bmake), '-r', '-m', '/', '-f', str(fixture), '-n',
                                     'pre-configure', 'post-install'], cwd=RECIPE,
                                    capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stdout + result.stderr)
            commands = [shlex.split(line) for line in result.stdout.splitlines()
                        if '/check-dynamic-elf.py ' in line]
            common = ['/selected/python3.15', '-B', '-E', '-S', str(CHECKER),
                      '--sdk-source', '/selected/sdk', '--arch', arch]
            require(commands == [common + ['--check-sdk'],
                                  common + ['--library-dir', '/selected/stage/usr/pkg/lib']],
                    'Actual native/cross recipe lost a mandatory ELF gate: ' + result.stdout)
            require(result.stdout.index('--check-sdk') < result.stdout.index('import sys, mako'),
                    'SDK capability check moved after configuration imports')
            cases += 1
    print('PASS: ' + str(cases) + ' real bmake native/cross source-hook queries; no commands executed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'bmake', 'work-parent'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(all(path.is_absolute() for path in vars(args).values()), 'Use absolute inputs')
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
    work = Path(tempfile.mkdtemp(prefix='mesa-dynamic-elf-', dir=args.work_parent))
    try:
        check_bytes(work / 'bytes', args.sdk_source)
        check_recipe(work / 'recipe', args.bmake)
    finally:
        print(subprocess.check_output(['df', '-k', str(work)], text=True), end='')
        shutil.rmtree(work)
        require(not work.exists(), 'Owned fixture remains')
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True), end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
