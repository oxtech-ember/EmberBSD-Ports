#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: LLVM compiler-rt standalone builtins CMake; AI-assisted Ports orchestration.
"""Build the first target runtime from the common LLVM source recipe."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys

sys.dont_write_bytecode = True


def require(condition, message):
    from emberbsd_sdk.errors import SDKError
    if not condition:
        raise SDKError(message)


def source_identity(ports, archive):
    """Use the common source pin, without another version or checksum."""
    from emberbsd_sdk import inventory
    recipe = Path(ports) / 'pkgsrc/lang/llvm'
    version = re.findall(r'^LLVM_VERSION=\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$',
                         (recipe / 'version.mk').read_text(), re.M)
    require(len(version) == 1, 'the common LLVM recipe must select one release')
    basename = 'llvm-project-' + version[0] + '.src.tar.xz'
    records = re.findall(r'^SHA512 \(' + re.escape(basename) + r'\) = ([a-f0-9]{128})$',
                         (recipe / 'distinfo').read_text(), re.M)
    require(len(records) == 1, 'the common LLVM archive SHA512 is missing or ambiguous')
    require(Path(archive).name == basename, 'archive name differs from the common LLVM recipe')
    require(inventory.hash_file(archive, 'sha512') == records[0], 'LLVM archive SHA512 differs')
    return dict(version=version[0], archive=basename, sha512=records[0])



def source_patches(ports):
    """Check all common LLVM patches and reject a new runtime source delta.

    These patches are rooted at llvm/, which is not compiled by this producer.
    The native LLVM CMake package and tools come from the complete Ports recipe.
    """
    from emberbsd_sdk import inventory
    root = Path(ports)
    require(not (root / 'pkgsrc/lang/compiler-rt').exists(),
            'connect the common compiler-rt recipe and its patches before using this producer')
    recipe = root / 'pkgsrc/lang/llvm'
    expected = dict(re.findall(r'^SHA1 \((patch-[^)]+)\) = ([a-f0-9]{40})$',
                               (recipe / 'distinfo').read_text(), re.M))
    patches = sorted((recipe / 'patches').glob('patch-*'))
    require(set(expected) == {path.name for path in patches}, 'LLVM patch inventory differs from distinfo')
    result = {}
    for path in patches:
        data = path.read_bytes()
        digest = hashlib.sha1(b''.join(line for line in data.splitlines(keepends=True)
                                      if b'$NetBSD' not in line)).hexdigest()
        require(digest == expected[path.name], 'LLVM patch checksum differs: ' + path.name)
        names = re.findall(rb'^(?:---|\+\+\+) ([^\t\n ]+)', data, re.M)
        require(bool(names), 'LLVM patch has no source paths: ' + path.name)
        for name in names:
            text = name.decode('ascii')
            require(not text.startswith('/') and all(part not in ('', '.', '..') for part in text.split('/')),
                    'LLVM patch has an unsupported source path: ' + path.name)
            require(text not in ('LICENSE.TXT', 'LICENSE.TXT.orig'),
                    'LLVM license patch must be applied to the selected runtime source')
        result[str(path.relative_to(root))] = inventory.sha256_file(path)
    return result


def header_inputs(base):
    """Record actual preliminary headers; no final application SDK is required."""
    from emberbsd_sdk import inventory
    for name in ('sys/param.h', 'stdint.h', 'limits.h'):
        inventory.required_file(base, 'usr/include/' + name)
    rows = inventory.snapshot_tree(str(Path(base) / 'usr/include'))
    files = {'usr/include/' + name: row['sha256'] for name, row in rows.items()
             if row['kind'] == 'file'}
    links = {'usr/include/' + name: row['target'] for name, row in rows.items()
             if row['kind'] == 'link'}
    return dict(files=files, symlinks=links)


def commands(work, base, target, version, native, compiler):
    """Use the upstream standalone builtins target with explicit cross inputs."""
    work = Path(work)
    triplet = target['triplet']
    source = work / 'source' / ('llvm-project-' + version + '.src')
    build = work / 'build'
    command = [native.tool('cmake'), '-S', str(source / 'compiler-rt/lib/builtins'),
               '-B', str(build), '-G', 'Ninja']
    values = dict(
        CMAKE_SYSTEM_NAME='NetBSD', CMAKE_SYSTEM_PROCESSOR=target['arch'],
        CMAKE_SYSROOT=str(base), CMAKE_BUILD_TYPE='Release',
        CMAKE_INSTALL_PREFIX='/usr/pkg/llvm', CMAKE_MAKE_PROGRAM=native.tool('ninja'),
        CMAKE_PROGRAM_PATH=str(Path(native.bundle_root) / 'bin'),
        CMAKE_TRY_COMPILE_TARGET_TYPE='STATIC_LIBRARY',
        CMAKE_POSITION_INDEPENDENT_CODE='ON', CMAKE_EXPORT_COMPILE_COMMANDS='ON',
        CMAKE_FIND_ROOT_PATH=str(base), CMAKE_FIND_ROOT_PATH_MODE_PROGRAM='NEVER',
        CMAKE_FIND_ROOT_PATH_MODE_LIBRARY='ONLY', CMAKE_FIND_ROOT_PATH_MODE_INCLUDE='ONLY',
        CMAKE_FIND_ROOT_PATH_MODE_PACKAGE='ONLY',
        CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH='OFF',
        CMAKE_FIND_USE_CMAKE_SYSTEM_PATH='OFF',
        CMAKE_C_COMPILER=compiler['binaries']['cc']['selected_path'],
        CMAKE_CXX_COMPILER=compiler['binaries']['cxx']['selected_path'],
        CMAKE_ASM_COMPILER=compiler['binaries']['cc']['selected_path'],
        CMAKE_C_COMPILER_TARGET=triplet, CMAKE_CXX_COMPILER_TARGET=triplet,
        CMAKE_ASM_COMPILER_TARGET=triplet,
        CMAKE_AR=compiler['binaries']['ar']['selected_path'],
        CMAKE_RANLIB=compiler['binaries']['ranlib']['selected_path'],
        CMAKE_NM=compiler['binaries']['nm']['selected_path'],
        CMAKE_STRIP=compiler['binaries']['strip']['selected_path'],
        CMAKE_LINKER=compiler['binaries']['ld']['selected_path'],
        Python3_EXECUTABLE=native.tool('python'),
        LLVM_CMAKE_DIR=str(Path(native.bundle_root) / 'lib/cmake/llvm'),
        LLVM_DIR=str(Path(native.bundle_root) / 'lib/cmake/llvm'),
        LLVM_OMIT_EXPORTS_FROM_CONFIG='ON',
        LLVM_MAIN_SRC_DIR=str(source / 'llvm'), LLVM_ENABLE_PER_TARGET_RUNTIME_DIR='OFF',
        COMPILER_RT_OS_DIR='netbsd', COMPILER_RT_DEFAULT_TARGET_ONLY='ON',
        COMPILER_RT_INSTALL_PATH__STRING='lib/clang/' + version.split('.')[0],
        COMPILER_RT_BUILTINS_ENABLE_PIC='ON', COMPILER_RT_INCLUDE_TESTS='OFF')
    # Do not set COMPILER_RT_DEFAULT_TARGET_TRIPLE with DEFAULT_TARGET_ONLY.
    # Upstream derives and normalizes that triple from CMAKE_C_COMPILER_TARGET.
    for role in ('C', 'CXX', 'ASM'):
        values['CMAKE_' + role + '_FLAGS'] = '--ld-path=' + compiler['binaries']['ld']['selected_path']
    command += ['-D' + key.replace('__', ':') + '=' + value for key, value in values.items()]
    return [command,
            [native.tool('cmake'), '--build', str(build), '--target', 'builtins'],
            [native.tool('cmake'), '--build', str(build), '--target', 'install-builtins']]


def plan(options):
    from emberbsd_sdk import inventory, llvm_runtime, paths, process, provenance, sourceprep
    from emberbsd_sdk.native_toolset import load_host_prefix
    from emberbsd_sdk.target_toolchain import clang_compiler
    from emberbsd_sdk.targets import target_definition
    require(llvm_runtime.LLVM_RUNTIME_API == 1 and sourceprep.SOURCE_PREPARATION_API == 2,
            'selected SDK lacks the common LLVM runtime/source interface')
    require(options.jobs > 0, 'jobs must be positive')
    require(options.git is not None, 'select Git for source inspection with --git')
    target = target_definition(options.target)
    selected = {}
    for name in ('ports', 'archive', 'base', 'os', 'host_prefix', 'git'):
        selected[name] = paths.build_path(paths.canonical_existing(getattr(options, name)))
    for name in ('ports', 'base', 'os', 'host_prefix'):
        paths.real_directory(selected[name])
    work = paths.build_path(paths.canonical_new(options.work))
    require(paths.entry(work) is None, 'work directory already exists; use a new owned component directory')
    paths.real_directory(os.path.dirname(work))
    for name, path in selected.items():
        paths.reject_overlap(work, path)
    env = process.sanitized_environment()
    sources = {name: provenance.git_source(selected[name], kind=name, git=selected['git'], env=env)
               for name in ('ports', 'os')}
    require(inventory.sha256_file(__file__) == inventory.sha256_file(
                Path(selected['ports']) / 'pkgsrc/lang/llvm/files/build-builtins.py'),
            'the selected Ports source differs from the running producer')
    identity = source_identity(selected['ports'], selected['archive'])
    patch_files = source_patches(selected['ports'])
    base = header_inputs(selected['base'])
    native = load_host_prefix(selected['host_prefix'], required_roles=(
        'cc', 'cxx', 'ar', 'ranlib', 'nm', 'strip', 'cmake', 'ninja', 'python', 'sh'))
    require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
            'run the build controller with the selected native Python')
    env.update(PATH=native.path, SHELL=native.tool('sh'),
               CMAKE_BUILD_PARALLEL_LEVEL=str(options.jobs),
               DESTDIR=str(Path(work) / 'stage'))
    compiler = clang_compiler(native.bundle_root, target['triplet'], host=native.host, env=env)
    require(compiler['version'] == identity['version'], 'Clang and common runtime versions differ')
    inventory.required_file(native.bundle_root, 'lib/cmake/llvm/LLVMConfig.cmake')
    recipe_names = ('pkgsrc/lang/llvm/version.mk', 'pkgsrc/lang/llvm/distinfo',
                    'pkgsrc/lang/llvm/files/build-builtins.py', 'pkgsrc/lang/llvm/files/sdk_source.py')
    recipe = dict(ports_revision=sources['ports']['commit'],
                  files={**{name: inventory.sha256_file(Path(selected['ports']) / name) for name in recipe_names},
                         **patch_files})
    return dict(format='emberbsd-builtins-build', version=1, target=options.target,
                target_definition=target, work=work, inputs=selected, sources=sources,
                source=identity, base=dict(os_revision=sources['os']['commit'], **base),
                recipe=recipe, compiler=compiler, native=native.as_dict(), environment=env,
                commands=commands(work, selected['base'], target, identity['version'], native, compiler),
                status='planned', target_execution='not-run',
                base_origin='caller-selected OS source; header producer origin is not verified',
                source_patch_scope='common LLVM patches affect native LLVM; no compiler-rt source patches')


def stage_record(build):
    from emberbsd_sdk import inventory, llvm_runtime
    stage = Path(build['work']) / 'stage'
    rows = inventory.snapshot_tree(str(stage), machine=build['target_definition']['elf'])
    artifacts = [name for name, row in rows.items() if row['kind'] == 'file' and
                 re.fullmatch(r'usr/pkg/llvm/lib/clang/[0-9]+/lib/netbsd/libclang_rt\.builtins-[A-Za-z0-9_]+\.a', name)]
    require(len(artifacts) == 1, 'installation must contain exactly one target builtins archive')
    allowed = {artifacts[0], 'usr/pkg/llvm/share/licenses/compiler-rt/LICENSE.TXT'}
    require({name for name, row in rows.items() if row['kind'] != 'directory'} == allowed,
            'unexpected file or link in builtins-only installation')
    record = dict(format='emberbsd-llvm-runtime', version=1, compiler_family='clang',
        llvm_version=build['source']['version'], components=['builtins'], target=build['target'],
        triplet=build['target_definition']['triplet'], machine_arch=build['target_definition']['arch'],
        elf_machine=build['target_definition']['elf'], prefix='usr/pkg/llvm',
        source={key: build['source'][key] for key in ('archive', 'sha512')},
        recipe=build['recipe'], base=build['base'], artifacts=dict(builtins=artifacts[0]),
        files={name: row['sha256'] for name, row in rows.items() if row['kind'] == 'file'},
        symlinks={name: row['target'] for name, row in rows.items() if row['kind'] == 'link'})
    llvm_runtime.validate_identity(record, target=build['target'], required_components=('builtins',))
    return record


def build(options):
    from emberbsd_sdk import inventory, jsonio, llvm_runtime, process, provenance, sourceprep
    result = plan(options)
    if options.plan:
        return result
    work = Path(result['work'])
    work.mkdir()  # Exclusive claim. No existing objects or partial stage is reused.
    source = work / 'source'
    source.mkdir()
    result['status'] = 'building'
    jsonio.write_json(work / 'build.json', result)
    try:
        sourceprep.extract_archive(result['inputs']['archive'], source,
            'llvm-project-' + result['source']['version'] + '.src', 'LLVM',
            components=('compiler-rt', 'cmake', 'third-party', 'libc', 'llvm/LICENSE.TXT'),
            max_members=500000, max_bytes=4 * 1024**3)
        for number, command in enumerate(result['commands']):
            process.run_logged(command, str(work / (str(number) + '.log')),
                               env=result['environment'], empty_snapshot_timeout=120)
        require(header_inputs(result['inputs']['base']) ==
                {key: result['base'][key] for key in ('files', 'symlinks')},
                'base headers changed during the build')
        require(source_patches(result['inputs']['ports']) ==
                {name: digest for name, digest in result['recipe']['files'].items() if '/patches/' in name},
                'common LLVM patch set changed during the build')
        require(source_identity(result['inputs']['ports'], result['inputs']['archive']) == result['source'],
                'common LLVM source changed during the build')
        from emberbsd_sdk.target_toolchain import clang_compiler
        require(clang_compiler(result['inputs']['host_prefix'], result['target_definition']['triplet'],
                    host=result['native']['host'], env=result['environment']) == result['compiler'],
                'selected target compiler changed during the build')
        for name, record in result['sources'].items():
            require(provenance.git_source(result['inputs'][name], kind=name, git=result['inputs']['git']) == record,
                    name + ' source changed during the build')
        license_source = source / ('llvm-project-' + result['source']['version'] + '.src') / 'compiler-rt/LICENSE.TXT'
        require(license_source.is_file(), 'compiler-rt license is missing from the common source')
        license_target = work / 'stage/usr/pkg/llvm/share/licenses/compiler-rt/LICENSE.TXT'
        license_target.parent.mkdir(parents=True, exist_ok=True)
        with license_source.open('rb') as original, license_target.open('xb') as installed:
            shutil.copyfileobj(original, installed)
        record = stage_record(result)
        jsonio.write_json(work / 'stage' / llvm_runtime.MANIFEST, record)
        llvm_runtime.validate_stage(work / 'stage', target=result['target'],
            required_components=('builtins',), ports=result['inputs']['ports'],
            ports_revision=result['sources']['ports']['commit'], base=result['inputs']['base'])
        result.update(status='built-and-inspected', runtime=record)
    except BaseException as error:
        result.update(status='failed', error=str(error))
        # A runtime manifest never marks failed or interrupted output complete.
        manifest = work / 'stage' / llvm_runtime.MANIFEST
        if manifest.exists():
            manifest.unlink()
        raise
    finally:
        jsonio.write_json(work / 'build.json', result, exclusive=False)
    return result


def main():
    from sdk_source import load_sdk, install_signal_handlers, exit_error
    _, arguments = load_sdk()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'base', 'os', 'host-prefix', 'work', 'target'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--ports', default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument('--git', default=shutil.which('git'), help='Git is used only for source inspection')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--plan', action='store_true')
    options = parser.parse_args(arguments)
    install_signal_handlers()
    try:
        import json
        print(json.dumps(build(options), indent=2))
    except Exception as error:
        exit_error(error)


if __name__ == '__main__':
    main()
