#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Boost acceptance preparation.
"""Build a GCC16 consumer of the normal installed Boost and ICU packages."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'sysroot', 'cross-tools', 'cmake', 'packages', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error('Select CPython 3.15.')
    sdk = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk import elf, inventory, jsonio, paths, process, provenance
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1 or Path(emberbsd_sdk.__file__).resolve().parent != sdk / 'src/emberbsd_sdk':
        parser.error('Select the explicit SDK source with host API 1.')
    owner = Path(__file__).resolve().parent
    ports = owner.parents[3]
    inputs = dict(sdk=provenance.git_source(str(sdk)), ports=provenance.git_source(str(ports), kind='ports'))
    sysroot = args.sysroot.resolve(strict=True)
    tools = args.cross_tools.resolve(strict=True)
    cmake = args.cmake.resolve(strict=True)
    packages = args.packages.resolve(strict=True)
    work = Path(paths.canonical_new(str(args.work)))
    for source in (sdk, ports, sysroot, tools, cmake, packages):
        paths.reject_overlap(str(work), str(source))
    for path in (sysroot, tools, cmake, work, owner):
        if re.fullmatch(r'[A-Za-z0-9_./+-]+', str(path)) is None:
            parser.error('CMake compiler flags require paths without whitespace or shell characters.')
    work.mkdir()
    (work / 'INCOMPLETE').write_text('Preparation has not completed.\n', encoding='utf-8')
    (work / 'logs').mkdir()
    bundle = work / 'bundle'
    (bundle / 'source').mkdir(parents=True)
    commands = []

    def run(label, argv):
        argv = [str(item) for item in argv]
        try:
            result = process.capture(argv, env=dict(os.environ, LC_ALL='C'))
        except CommandError as error:
            (work / 'logs' / (label + '.stdout')).write_bytes(error.stdout)
            (work / 'logs' / (label + '.stderr')).write_bytes(error.stderr)
            commands.append(dict(label=label, argv=argv, status=error.returncode))
            jsonio.write_json(work / 'commands.json', commands, exclusive=False)
            raise
        (work / 'logs' / (label + '.stdout')).write_bytes(result.stdout)
        (work / 'logs' / (label + '.stderr')).write_bytes(result.stderr)
        commands.append(dict(label=label, argv=argv, status=result.returncode))
        jsonio.write_json(work / 'commands.json', commands, exclusive=False)
        return result.stdout.decode('utf-8')

    cxx = tools / 'bin/aarch64--netbsd-g++'
    if run('compiler-version', [cxx, '-dumpfullversion']).strip() != '16.2.0' or run('compiler-target', [cxx, '-dumpmachine']).strip() != 'aarch64--netbsd':
        raise ValueError('Select the common GCC 16.2.0 AArch64 compiler.')
    inputs['compiler'] = dict(path=str(cxx), sha256=inventory.sha256_file(cxx.resolve()), version=run('compiler-identity', [cxx, '--version']))
    inputs['python'] = dict(path=sys.executable, version=sys.version, sha256=inventory.sha256_file(Path(sys.executable).resolve()))
    inputs['cmake'] = dict(path=str(cmake), sha256=inventory.sha256_file(cmake), version=run('cmake-version', [cmake, '--version']))
    selected = ('boost-headers-1.92.0', 'boost-libs-1.92.0nb1', 'icu-79.1nb1', 'icu-devel-79.1nb1', 'gcc16-runtime-16.2.0nb3')
    inputs['packages'] = {}
    for name in selected:
        archive = packages / (name + '.tgz')
        catalog = sysroot / 'usr/pkg/pkgdb' / name / '+CONTENTS'
        with tarfile.open(archive, 'r:gz') as package:
            members = package.getmembers()
            if len({member.name for member in members}) != len(members):
                raise ValueError('Duplicate package entries: ' + name)
            if package.extractfile('+CONTENTS').read() != catalog.read_bytes():
                raise ValueError('Installed package catalog differs: ' + name)
            for member in members:
                relative = Path(member.name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Unsafe package path: ' + member.name)
                if member.name.startswith('+') or member.isdir():
                    continue
                installed = sysroot / 'usr/pkg' / relative
                if not installed.resolve(strict=True).is_relative_to(sysroot):
                    raise ValueError('Installed path escapes the SDK: ' + member.name)
                if member.isfile() or member.islnk():
                    expected = hashlib.file_digest(package.extractfile(member), 'sha256').hexdigest()
                    if installed.is_symlink() or inventory.sha256_file(installed) != expected or stat.S_IMODE(installed.stat().st_mode) != member.mode & 0o7777:
                        raise ValueError('Installed package file differs: ' + member.name)
                elif member.issym():
                    if not installed.is_symlink() or os.readlink(installed) != member.linkname:
                        raise ValueError('Installed package link differs: ' + member.name)
                else:
                    raise ValueError('Unsupported package entry: ' + member.name)
        inputs['packages'][name] = dict(sha256=inventory.sha256_file(archive), catalog_sha256=inventory.sha256_file(catalog))
    loaded = owner / '../../../common-graphics/cross/gui-cad-api/loaded.h'
    for source in sorted(owner.iterdir()):
        if source.is_file():
            shutil.copy2(source, bundle / 'source' / source.name)
    if not (bundle / 'source/loaded.h').exists():
        shutil.copy2(loaded.resolve(strict=True), bundle / 'source/loaded.h')
    inputs['sources'] = {source.name: inventory.sha256_file(source) for source in (bundle / 'source').iterdir()}
    flags = [f'--sysroot={sysroot}', f'-B{sysroot}/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/', '-O2', '-g', '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error', '-fno-sanitize-recover=all', f'-L{sysroot}/usr/pkg/gcc16/lib', f'-Wl,-rpath-link,{sysroot}/usr/pkg/lib', f'-Wl,-rpath-link,{sysroot}/usr/pkg/gcc16/lib']
    build = work / 'cmake-build'
    run('configure', [cmake, '-S', bundle / 'source', '-B', build, '-DCMAKE_SYSTEM_NAME=NetBSD', '-DCMAKE_SYSTEM_PROCESSOR=aarch64', f'-DCMAKE_SYSROOT={sysroot}', f'-DCMAKE_CXX_COMPILER={cxx}', '-DCMAKE_CXX_FLAGS=' + ' '.join(flags), f'-DCMAKE_FIND_ROOT_PATH={sysroot}', '-DCMAKE_PREFIX_PATH=/usr/pkg', '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER', '-DBoost_USE_STATIC_LIBS=OFF', '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON', '-DCMAKE_INSTALL_RPATH=/usr/pkg/gcc16/lib;/usr/pkg/lib', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'])
    run('build', [cmake, '--build', build, '--parallel', '1', '--verbose'])
    executable = build / 'boost-api'
    elf.read_elf_header(str(executable), 183)
    info = elf.read_elf_dynamic(str(executable), machine=183)
    if 'libstdc++.so.7' not in info['needed'] or any(name.startswith('libstdc++.so.') and name != 'libstdc++.so.7' for name in info['needed']):
        raise ValueError('Consumer did not select the common GCC16 C++ ABI.')
    shutil.copy2(executable, bundle / 'boost-api')
    shutil.copy2(build / 'compile_commands.json', work / 'compile_commands.json')
    directories = [sysroot / name for name in ('usr/pkg/gcc16/lib', 'usr/pkg/lib', 'usr/lib', 'lib')]
    libraries, providers = {}, {}
    common_cpp = (sysroot / 'usr/pkg/gcc16/lib/libstdc++.so.7').resolve(strict=True)

    def visit(path):
        path = path.resolve(strict=True)
        if not path.is_relative_to(sysroot):
            raise ValueError('A runtime library escapes the SDK.')
        if path.name.startswith('libstdc++.so.') and path != common_cpp:
            raise ValueError('A runtime dependency selected a different C++ ABI.')
        target = '/' + str(path.relative_to(sysroot))
        if target in libraries:
            return
        libraries[target] = inventory.sha256_file(path)
        for needed in elf.read_elf_dynamic(str(path), machine=183)['needed']:
            if '/' in needed:
                raise ValueError('Unsafe DT_NEEDED name.')
            candidates = [directory / needed for directory in directories if (directory / needed).is_file()]
            if not candidates:
                raise ValueError('Missing runtime provider: ' + needed)
            provider = candidates[0].resolve(strict=True)
            if providers.setdefault(needed, provider) != provider:
                raise ValueError('Conflicting runtime providers: ' + needed)
            visit(provider)

    for needed in info['needed']:
        candidates = [directory / needed for directory in directories if (directory / needed).is_file()]
        if not candidates:
            raise ValueError('Missing consumer runtime provider: ' + needed)
        visit(candidates[0])
    required = [sysroot / 'usr/pkg/gcc16/lib/libstdc++.so.7', sysroot / 'usr/pkg/gcc16/lib/libgcc_s.so.1', *(sysroot / 'usr/pkg/lib' / ('libboost_' + name + '.so.1.92.0') for name in ('locale', 'filesystem', 'thread', 'unit_test_framework'))]
    required_targets = ['/' + str(path.resolve(strict=True).relative_to(sysroot)) for path in required]
    if any(target not in libraries for target in required_targets):
        raise ValueError('Required installed providers are absent from the consumer closure.')
    (bundle / 'required-providers.txt').write_text(''.join(target + '\n' for target in required_targets), encoding='utf-8')
    (bundle / 'runtime.sha256').write_text(''.join(digest + '  ' + target + '\n' for target, digest in sorted(libraries.items())), encoding='utf-8')
    shutil.copy2(owner / 'run.sh', bundle / 'run.sh')
    jsonio.write_json(bundle / 'inputs.json', inputs)
    (bundle / 'artifacts.sha256').write_text(''.join(inventory.sha256_file(path) + '  ' + str(path.relative_to(bundle)) + '\n' for path in sorted(bundle.rglob('*')) if path.is_file()), encoding='utf-8')
    archive = work / 'boost-api.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        for path in sorted(bundle.rglob('*')):
            output.add(path, arcname=str(path.relative_to(bundle)), recursive=False)
    (work / 'archive.sha256').write_text(inventory.sha256_file(archive) + '\n', encoding='utf-8')
    (work / 'INCOMPLETE').unlink()
    print(str(archive))
    print(inventory.sha256_file(archive))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        status = getattr(error, 'returncode', 1)
        raise SystemExit(status if status >= 0 else 128 - status)
