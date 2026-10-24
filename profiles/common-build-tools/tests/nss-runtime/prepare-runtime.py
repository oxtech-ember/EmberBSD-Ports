#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Cross-build the bounded NSS 3.132 target runtime smoke test with GCC16."""
import argparse
from pathlib import Path
import os
import shutil
import sys
sys.dont_write_bytecode = True


def verify_nss_recipe_pin(recipe_text):
    lines = recipe_text.splitlines()
    expected = (
        '-DISTNAME=\t\tnss-3.129',
        '+DISTNAME=\t\tnss-3.132',
    )
    matches = sum(
        1 for index in range(len(lines) - 1)
        if (lines[index], lines[index + 1]) == expected
    )
    if matches != 1 or any(line.startswith('+PKGREVISION=') for line in lines):
        raise ValueError('The selected Ports patch does not pin NSS 3.132 exactly once.')


def verify_package_identity(contents, expected_name):
    identity = '@name ' + expected_name
    if contents.splitlines().count(identity) != 1:
        raise ValueError('Package metadata does not identify ' + expected_name + ' exactly once.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--ports-root', required=True, type=Path)
    parser.add_argument('--cross-tools', required=True, type=Path)
    parser.add_argument('--sysroot', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--target', choices=('amd64', 'aarch64'), default='amd64')
    args = parser.parse_args()

    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
        parser.error('Use CPython 3.15.')
    for name in ('sdk_source', 'ports_root', 'cross_tools', 'sysroot', 'work'):
        if not getattr(args, name).is_absolute():
            parser.error('--' + name.replace('_', '-') + ' must be absolute.')

    sdk_root = args.sdk_source.resolve(strict=True)
    sdk_src = sdk_root / 'src'
    sdk_package = (sdk_src / 'emberbsd_sdk').resolve(strict=True)
    sys.path.insert(0, str(sdk_src))
    import emberbsd_sdk
    from emberbsd_sdk import elf, inventory, jsonio, paths, process
    from emberbsd_sdk.errors import CommandError
    if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
        parser.error('The selected SDK must provide API version 1.')
    if Path(emberbsd_sdk.__file__).resolve().parent != sdk_package:
        parser.error('emberbsd_sdk did not load from the explicitly selected SDK.')
    for module in (elf, inventory, jsonio, paths, process):
        if not Path(module.__file__).resolve().is_relative_to(sdk_package):
            parser.error('An SDK module loaded from outside the selected SDK.')

    ports_root = args.ports_root.resolve(strict=True)
    cross_tools = args.cross_tools.resolve(strict=True)
    sysroot = args.sysroot.resolve(strict=True)
    source_dir = Path(__file__).resolve().parent
    work = Path(paths.canonical_new(args.work))
    if work.exists() or work.is_symlink():
        parser.error('The output directory must not already exist.')
    for item in (sdk_root, ports_root, cross_tools, sysroot, source_dir):
        paths.reject_overlap(str(work), str(item))

    targets = {
        'amd64': ('x86_64--netbsd', 62),
        'aarch64': ('aarch64--netbsd', 183),
    }
    triplet, machine = targets[args.target]
    cc = cross_tools / 'bin' / (triplet + '-gcc')
    if not cc.is_file():
        parser.error('Missing selected GCC16 target compiler: ' + str(cc))

    prefix = sysroot / 'usr/pkg'
    pkgdb = prefix / 'pkgdb'
    nss_package = pkgdb / 'nss-3.132' / '+CONTENTS'
    nspr_packages = sorted(pkgdb.glob('nspr-4.40*/+CONTENTS'))
    if not nss_package.is_file():
        parser.error('Install the matching nss-3.132 runtime package first.')
    if len(nspr_packages) != 1:
        parser.error('Install exactly one NSPR 4.40 runtime package first.')
    nspr_package = nspr_packages[0]

    nss_plist = ports_root / 'upstream/pkgsrc/devel/nss/PLIST'
    nspr_plist = ports_root / 'upstream/pkgsrc/devel/nspr/PLIST'
    recipe_patch = ports_root / 'profiles/common-build-tools/patches/pkgsrc-nss-cross-host-tools.patch'
    for path in (nss_plist, nspr_plist, recipe_patch):
        if not path.is_file():
            parser.error('The selected Ports tree is missing package provenance: ' + str(path))
    nss_payload = (
        'lib/nss/libnss3.so',
        'lib/nss/libnssutil3.so',
        'lib/nss/libsoftokn3.so',
        'lib/nss/libfreebl3.so',
    )
    nspr_payload = (
        'lib/nspr/libnspr4.so',
        'lib/nspr/libplc4.so',
        'lib/nspr/libplds4.so',
    )
    nss_plist_lines = set(nss_plist.read_text(encoding='utf-8').splitlines())
    nspr_plist_lines = set(nspr_plist.read_text(encoding='utf-8').splitlines())
    if any(path not in nss_plist_lines for path in nss_payload):
        parser.error('The pinned NSS PLIST is missing required runtime payload.')
    if any(path not in nspr_plist_lines for path in nspr_payload):
        parser.error('The pinned NSPR PLIST is missing required runtime payload.')
    try:
        verify_nss_recipe_pin(recipe_patch.read_text(encoding='utf-8'))
        verify_package_identity(nss_package.read_text(encoding='utf-8'), 'nss-3.132')
        verify_package_identity(nspr_package.read_text(encoding='utf-8'), 'nspr-4.40')
    except ValueError as error:
        parser.error(str(error))

    nss_lib = prefix / 'lib/nss'
    nspr_lib = prefix / 'lib/nspr'
    headers = prefix / 'include'
    required = {
        nss_lib / 'libnss3.so': 'libnss3.so',
        nss_lib / 'libnssutil3.so': 'libnssutil3.so',
        nss_lib / 'libsoftokn3.so': 'libsoftokn3.so',
        nss_lib / 'libfreebl3.so': 'libfreebl3.so',
        nspr_lib / 'libnspr4.so': 'libnspr4.so',
        nspr_lib / 'libplc4.so': 'libplc4.so',
        nspr_lib / 'libplds4.so': 'libplds4.so',
    }
    for path, soname in required.items():
        if not path.is_file():
            parser.error('Required NSS/NSPR runtime payload is missing: ' + str(path))
        resolved = path.resolve(strict=True)
        dynamic = elf.read_elf_dynamic(resolved, machine=machine)
        header = elf.read_elf_header(resolved, machine=machine, required_type=3)
        if header['class'] != 64 or header['endian'] != 'little' or dynamic['soname'] != soname:
            parser.error('Wrong target ELF class, byte order, or SONAME: ' + str(path))

    header_paths = [
        headers / 'nss/nss.h',
        headers / 'nss/pk11pub.h',
        headers / 'nss/secerr.h',
        headers / 'nss/secoidt.h',
        headers / 'nss/secport.h',
        headers / 'nspr/prtypes.h',
        headers / 'nspr/prerror.h',
    ]
    for path in header_paths:
        if not path.is_file():
            parser.error('Required NSS/NSPR SDK header is missing: ' + str(path))

    gcc_prefix = prefix / 'gcc16/lib/gcc' / triplet / '16.2.0'
    gcc_runtime = prefix / 'gcc16/lib'
    if not gcc_prefix.is_dir() or not gcc_runtime.is_dir():
        parser.error('The matching GCC16 target runtime is missing from the sysroot.')

    work.mkdir(mode=0o700)
    temp = work / 'tmp'
    temp.mkdir()
    env = process.sanitized_environment()
    env.update(TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp))
    commands = []

    def run(label, argv):
        command = [str(item) for item in argv]
        try:
            result = process.capture(command, cwd=str(work), env=env)
            status, stdout, stderr = result.returncode, result.stdout, result.stderr
        except CommandError as error:
            status, stdout, stderr = error.returncode, error.stdout, error.stderr
        (work / (label + '.stdout')).write_bytes(stdout)
        (work / (label + '.stderr')).write_bytes(stderr)
        commands.append({'label': label, 'argv': command, 'cwd': str(work), 'status': status})
        jsonio.write_json(work / 'commands.json', commands, exclusive=False)
        if status != 0:
            raise RuntimeError(f'{label} failed with status {status}; see {work}')
        return stdout.decode('utf-8', 'replace').strip()

    compiler_version = run('compiler-version', [cc, '-dumpfullversion'])
    compiler_target = run('compiler-target', [cc, '-dumpmachine'])
    if compiler_version != '16.2.0' or compiler_target != triplet:
        raise RuntimeError('The selected compiler is not the matching GCC 16.2.0 target.')

    fixture = source_dir / 'nss-runtime-smoke.c'
    run_script = source_dir / 'run.sh'
    source_hashes = {
        str(fixture): inventory.sha256_file(fixture),
        str(run_script): inventory.sha256_file(run_script),
    }
    input_paths = [
        cc, *header_paths, *required, nss_package, nspr_package,
        nss_plist, nspr_plist, recipe_patch,
    ]
    input_hashes = {
        str(path.resolve(strict=True)): inventory.sha256_file(path.resolve(strict=True))
        for path in input_paths
    }

    binary = work / 'nss-runtime-smoke'
    flags = [
        '--sysroot=' + str(sysroot),
        '-B' + str(gcc_prefix) + '/',
        '-B' + str(gcc_runtime) + '/',
        '-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
        '-Wformat=2', '-Wformat-signedness', '-pthread',
        '-I' + str(headers / 'nss'),
        '-I' + str(headers / 'nspr'),
    ]
    link = [
        '-L' + str(nss_lib),
        '-L' + str(nspr_lib),
        '-L' + str(gcc_runtime),
        '-Wl,-rpath,/usr/pkg/lib/nss:/usr/pkg/lib/nspr:/usr/pkg/gcc16/lib',
        '-Wl,-rpath-link,' + str(nss_lib),
        '-Wl,-rpath-link,' + str(nspr_lib),
        '-Wl,-rpath-link,' + str(gcc_runtime),
        '-Wl,-rpath-link,' + str(sysroot / 'usr/lib'),
        '-Wl,-rpath-link,' + str(sysroot / 'lib'),
        '-lnss3', '-lnssutil3', '-pthread',
    ]
    command = [str(cc), *flags, str(fixture), *link, '-o', str(binary)]
    run('compile', command)

    executable = elf.read_elf_dynamic(binary, machine=machine)
    binary_header = elf.read_elf_header(binary, machine=machine)
    if (binary_header['class'] != 64 or binary_header['endian'] != 'little' or
            binary_header['type'] not in (2, 3)):
        raise RuntimeError('The smoke binary is not a target ELF64 little-endian executable.')
    search_path = executable['rpath'] or executable['runpath'] or ''
    for expected in ('/usr/pkg/lib/nss', '/usr/pkg/lib/nspr', '/usr/pkg/gcc16/lib'):
        if expected not in search_path:
            raise RuntimeError('The smoke binary is missing target runtime path ' + expected)
    if any(str(path) in search_path for path in (work, sysroot, cross_tools)):
        raise RuntimeError('A host or build path leaked into the target runtime path.')

    shutil.copyfile(run_script, work / 'run.sh')
    os.chmod(work / 'run.sh', 0o755)
    if source_hashes != {
        str(fixture): inventory.sha256_file(fixture),
        str(run_script): inventory.sha256_file(run_script),
    }:
        raise RuntimeError('A public regression input changed during compilation.')
    if input_hashes != {
        str(path): inventory.sha256_file(path) for path in input_hashes
    }:
        raise RuntimeError('An installed target NSS/NSPR input changed during compilation.')

    jsonio.write_json(work / 'receipt.json', {
        'test': 'nss-runtime-smoke',
        'target': {'architecture': args.target, 'triplet': triplet, 'elf_machine': machine},
        'nss_version': '3.132',
        'sdk': {'root': str(sdk_root), 'api_version': 1},
        'compiler': {'path': str(cc), 'version': compiler_version, 'target': compiler_target},
        'input_sha256': {**source_hashes, **input_hashes},
        'runtime_payload': {
            'nss': list(nss_payload),
            'nspr': list(nspr_payload),
            'gcc16': 'libgcc_s from the matching target runtime when present in DT_NEEDED',
        },
        'binary_sha256': inventory.sha256_file(binary),
        'commands': commands,
        'scope': 'NSS 3.132 no-database C API lifecycle, SHA-256 known-answer, invalid digest length, internal token, and random-output smoke; no TLS, FIPS, database, network, or secret acceptance.',
        'status': 'built; target execution pending',
    }, exclusive=True)
    print('Built target NSS runtime smoke test: ' + str(binary))
    print('Copy the binary and run.sh to an EmberBSD target with the matching NSS/NSPR runtime packages.')


if __name__ == '__main__':
    main()
