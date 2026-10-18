#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted installed GUI/CAD API consumer preparation.
"""Build consumers with GCC16. Do not install packages or start a target."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--sysroot', required=True, type=Path)
    parser.add_argument('--cross-tools', required=True, type=Path)
    parser.add_argument('--cmake', required=True, type=Path)
    parser.add_argument('--packages', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15):
        parser.error('use the selected CPython 3.15 host profile')
    sdk_source = args.sdk_source.resolve(strict=True)
    sys.path.insert(0, str(sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.elf import read_elf_dynamic, read_elf_header
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.provenance import git_source
    if emberbsd_sdk.API_VERSION != 1:
        parser.error('require EmberBSD SDK host API 1')
    owner = Path(__file__).resolve().parent
    ports = owner.parents[3]
    inputs = {'sdk_source': git_source(str(sdk_source)),
              'ports_source': git_source(str(ports), kind='ports')}
    sysroot = args.sysroot.resolve(strict=True)
    tools = args.cross_tools.resolve(strict=True)
    packages = args.packages.resolve(strict=True)
    cmake = args.cmake.resolve(strict=True)
    work = args.work
    if not work.is_absolute() or work.exists() or work.is_symlink():
        parser.error('--work must be a new absolute path')
    if work.parent.resolve(strict=True) != work.parent:
        parser.error('--work must have real existing ancestors')
    for source in (sysroot, tools, packages, ports, sdk_source):
        if work.is_relative_to(source) or source.is_relative_to(work):
            parser.error('work must not overlap an input tree')
    cc = tools / 'bin/aarch64--netbsd-gcc'
    cxx = tools / 'bin/aarch64--netbsd-g++'
    work.mkdir(parents=True)
    incomplete = work / 'INCOMPLETE'
    incomplete.write_text('The producer has not completed.\n', encoding='utf-8')
    bundle = work / 'bundle'
    (bundle / 'bin').mkdir(parents=True)
    (bundle / 'source').mkdir()
    (work / 'logs').mkdir()
    commands = []
    environment = os.environ.copy()
    environment['LC_ALL'] = 'C'

    def run(argv, label, cwd=None):
        argv = [str(value) for value in argv]
        commands.append({'argv': argv, 'cwd': str(cwd) if cwd else None})
        result = subprocess.run(argv, cwd=cwd, env=environment,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=300, check=False)
        (work / 'logs' / (label + '.log')).write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(f'{label} failed with status {result.returncode}; see its log')
        return result.stdout.decode('utf-8', 'strict')

    for name, executable in (('cc', cc), ('cxx', cxx)):
        version = run([executable, '--version'], name + '-version')
        if '(GCC) 16.2.0' not in version.splitlines()[0]:
            raise RuntimeError('require the common GCC 16.2.0 compiler')
        inputs[name] = {'path': str(executable), 'resolved': str(executable.resolve()),
                        'sha256': sha256_file(str(executable.resolve())), 'version': version}
    inputs['python'] = {'path': sys.executable, 'resolved': str(Path(sys.executable).resolve()),
                        'version': sys.version, 'sha256': sha256_file(str(Path(sys.executable).resolve()))}
    inputs['cmake'] = {'path': str(cmake), 'sha256': sha256_file(str(cmake)),
                       'version': run([cmake, '--version'], 'cmake-version')}
    source_files = sorted(path for path in owner.iterdir() if path.is_file())
    inputs['sources'] = {path.name: sha256_file(str(path)) for path in source_files}
    for path in source_files:
        shutil.copy2(path, bundle / 'source' / path.name)

    selected = {}
    for name in ('glu-9.0.3', 'cairo-1.18.6', 'glm-1.0.3nb1', 'glew-2.3.1'):
        # Package names are explicit. Never accept a different installed provider.
        archive = packages / (name + '.tgz')
        catalog = sysroot / 'usr/pkg/pkgdb' / name / '+CONTENTS'
        with tarfile.open(archive, 'r:gz') as package:
            names = package.getmembers()
            if len({entry.name for entry in names}) != len(names):
                raise RuntimeError(f'duplicate package path: {archive}')
            contents = package.extractfile('+CONTENTS').read()
            if contents != catalog.read_bytes():
                raise RuntimeError(f'installed package catalog differs: {name}')
            for entry in names:
                relative = Path(entry.name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise RuntimeError(f'unsafe package path: {entry.name}')
                if entry.name.startswith('+') or entry.isdir():
                    continue
                target = sysroot / 'usr/pkg' / relative
                if not target.resolve(strict=True).is_relative_to(sysroot):
                    raise RuntimeError(f'installed package path escapes the SDK: {target}')
                if entry.isfile():
                    expected = hashlib.file_digest(package.extractfile(entry), 'sha256').hexdigest()
                    if target.is_symlink() or sha256_file(str(target)) != expected:
                        raise RuntimeError(f'installed package file differs: {target}')
                elif entry.issym():
                    if not target.is_symlink() or os.readlink(target) != entry.linkname:
                        raise RuntimeError(f'installed package link differs: {target}')
                else:
                    raise RuntimeError(f'unsupported package entry: {entry.name}')
        selected[name] = {'sha256': sha256_file(str(archive)),
                          'catalog_sha256': sha256_file(str(catalog))}
        shutil.copy2(catalog, bundle / 'source' / (name + '.CONTENTS'))
    inputs['packages'] = selected
    common = [f'--sysroot={sysroot}', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
              '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error',
              '-fno-sanitize-recover=all', f'-I{sysroot}/usr/pkg/include',
              f'-L{sysroot}/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/lib:/usr/pkg/gcc16/lib',
              f'-Wl,-rpath-link,{sysroot}/usr/pkg/lib',
              f'-Wl,-rpath-link,{sysroot}/usr/pkg/gcc16/lib']
    compile_commands = []
    for name, extra, libraries in (
            ('glu-api', [], ['-lGLU', '-lGL', '-lm']),
            ('cairo-api', [f'-I{sysroot}/usr/pkg/include/cairo'], ['-lcairo', '-lm']),
            ('glew-egl', [], ['-lGLEW', '-lEGL', '-lGL', '-lX11', '-lpthread'])):
        source = owner / (name + '.c')
        argv = [cc, *common, *extra, source, *libraries, '-o', bundle / 'bin' / name]
        run(argv, name)
        compile_commands.append({'directory': str(work), 'file': str(source),
                                 'arguments': [str(value) for value in argv]})

    # Use the actual installed CMake package. GLM has no pkg-config file.
    cmake_work = work / 'glm-cmake'
    flags = ' '.join(common)
    run([cmake, '-S', owner, '-B', cmake_work, '-DCMAKE_SYSTEM_NAME=NetBSD',
         '-DCMAKE_SYSTEM_PROCESSOR=aarch64', f'-DCMAKE_SYSROOT={sysroot}',
         f'-DCMAKE_C_COMPILER={cc}', f'-DCMAKE_CXX_COMPILER={cxx}',
         f'-DCMAKE_C_FLAGS={flags}', f'-DCMAKE_CXX_FLAGS={flags}',
         '-DCMAKE_BUILD_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib',
         f'-DCMAKE_FIND_ROOT_PATH={sysroot}', '-DCMAKE_PREFIX_PATH=/usr/pkg',
         '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY',
         '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY',
         '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY',
         '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER',
         '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], 'glm-configure')
    run([cmake, '--build', cmake_work, '--parallel', '1', '--verbose'], 'glm-build')
    shutil.copy2(cmake_work / 'glm-api', bundle / 'bin/glm-api')
    compile_commands.extend(json.loads((cmake_work / 'compile_commands.json').read_text(encoding='utf-8')))
    (work / 'compile_commands.json').write_text(json.dumps(compile_commands, indent=2) + '\n', encoding='utf-8')

    # These directories select the common GCC16 runtime before the base namesake.
    # The target runner checks the actual loaded canonical paths against this set.
    directories = [sysroot / name for name in ('usr/pkg/gcc16/lib', 'usr/pkg/lib', 'usr/lib', 'lib')]
    runtime = {}
    objects = {}
    chosen = {}

    def visit(path):
        path = path.resolve(strict=True)
        if not path.is_relative_to(sysroot):
            raise RuntimeError(f'runtime path escapes the SDK: {path}')
        target = '/' + str(path.relative_to(sysroot))
        if target in runtime:
            return
        runtime[target] = sha256_file(str(path))
        info = read_elf_dynamic(str(path), machine=183)
        objects[target] = info
        for soname in info['needed']:
            if '/' in soname or not soname:
                raise RuntimeError(f'unsafe DT_NEEDED: {soname}')
            candidates = [directory / soname for directory in directories if (directory / soname).is_file()]
            if not candidates:
                raise RuntimeError(f'no installed provider for {soname}')
            provider = candidates[0].resolve(strict=True)
            previous = chosen.setdefault(soname, provider)
            if previous != provider:
                raise RuntimeError(f'conflicting provider for {soname}')
            visit(provider)

    for binary in sorted((bundle / 'bin').iterdir()):
        header = read_elf_header(str(binary), machine=183)
        if header is None or header['type'] not in (2, 3):
            raise RuntimeError(f'not an AArch64 executable: {binary}')
        info = read_elf_dynamic(str(binary), machine=183)
        objects['bin/' + binary.name] = info
        for soname in info['needed']:
            candidates = [directory / soname for directory in directories if (directory / soname).is_file()]
            if not candidates:
                raise RuntimeError(f'no installed provider for {soname}')
            visit(candidates[0])
    visit(sysroot / 'libexec/ld.elf_so')
    # EGL opens the selected software driver. Include its real dependency closure.
    gallium = sysroot / 'usr/pkg/lib/libgallium-26.2.4.so'
    if gallium.exists():
        visit(gallium)
    else:
        raise RuntimeError('require the current Mesa 26.2.4 software driver')
    # A C-only process follows the fork libm's /lib RPATH. C++ consumers
    # already load the common GCC16 provider before libm. Retain both genuine
    # SDK files, but require exactly the appropriate provider in each process.
    libm = read_elf_dynamic(str((sysroot / 'usr/lib/libm.so.0').resolve(strict=True)), machine=183)
    if ('libgcc_s.so.1' not in libm['needed'] or
            libm['rpath'] != '/lib'):
        raise RuntimeError('the fork libm provider policy changed; review actual loader selection')
    base_gcc = (sysroot / 'lib/libgcc_s.so.1').resolve(strict=True)
    if read_elf_dynamic(str(base_gcc), machine=183)['soname'] != 'libgcc_s.so.1':
        raise RuntimeError('unexpected base compiler-support SONAME')
    visit(base_gcc)
    common_gcc = (sysroot / 'usr/pkg/gcc16/lib/libgcc_s.so.1').resolve(strict=True)
    if base_gcc == common_gcc:
        raise RuntimeError('base and common GCC16 provider identities must remain distinct')
    required = {'cairo-api': base_gcc, 'glu-api': common_gcc,
                'glm-api': common_gcc, 'glew-egl': common_gcc}
    (bundle / 'required-providers.tsv').write_text(
        ''.join(f'{name}\t/{path.relative_to(sysroot)}\n'
                for name, path in sorted(required.items())), encoding='utf-8')
    (bundle / 'runtime-libraries.sha256').write_text(
        ''.join(f'{digest}  {name}\n' for name, digest in sorted(runtime.items())), encoding='utf-8')
    (work / 'objects.json').write_text(json.dumps(objects, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(owner / 'run.sh', bundle / 'run.sh')
    (bundle / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n', encoding='utf-8')
    (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8')
    entries = sorted(path for path in bundle.rglob('*') if path.is_file())
    (bundle / 'artifacts.sha256').write_text(
        ''.join(f'{sha256_file(str(path))}  {path.relative_to(bundle)}\n' for path in entries), encoding='utf-8')
    archive = work / 'gui-cad-api.tar.gz'
    with tarfile.open(archive, 'w:gz') as output:
        for path in sorted(bundle.rglob('*')):
            output.add(path, arcname=str(path.relative_to(bundle)), recursive=False)
    (work / 'archive.sha256').write_text(sha256_file(str(archive)) + '\n', encoding='utf-8')
    incomplete.unlink()
    print(archive)
    print(sha256_file(str(archive)))


if __name__ == '__main__':
    main()
