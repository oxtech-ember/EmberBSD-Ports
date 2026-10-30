# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build fixed freestanding ABI profiles from the common runtime source."""
import os
from pathlib import Path
import shutil
import sys

PROFILES = {
    'wasm32-wasip1': dict(system='WASI', processor='wasm32', linker='wasm-ld', flags='', pic=False,
        artifact='lib/wasm32-unknown-wasip1/libclang_rt.builtins.a',
        manifest='wasi-builtins.json', format='emberbsd-wasi-builtins'),
    'riscv32-unknown-elf': dict(system='Generic', processor='riscv32', linker='elf-ld', pic=True,
        flags='--no-default-config -march=rv32imac_zicsr_zifencei -mabi=ilp32 -ffreestanding',
        artifact='lib/riscv32-unknown-unknown-elf/libclang_rt.builtins.a',
        manifest='freestanding-builtins.json', format='emberbsd-freestanding-builtins'),
}
LICENSES = ('LICENSE.TXT', 'CREDITS.TXT', 'LICENSE.EmberBSD-BINARY128.TXT', 'LICENSE.EmberBSD-GCOV.TXT')


def stage_rows(owner, stage, profile):
    artifact = profile['artifact']
    rows = owner.inventory.snapshot_tree(str(stage), exclude=(profile['manifest'],))
    owner.require(artifact in rows and rows[artifact]['kind'] == 'file',
                  'freestanding builtins archive is missing')
    expected = {artifact} | {'share/licenses/compiler-rt/' + name for name in LICENSES}
    owner.require({name for name, row in rows.items() if row['kind'] == 'file'} == expected and
                  all(row['kind'] in ('file', 'directory') for row in rows.values()),
                  'unexpected freestanding builtins stage content')
    return rows


def verify(owner, args, target):
    profile = PROFILES[target]
    source = Path(owner.paths.canonical_existing(args.source))
    stage = Path(owner.paths.canonical_existing(args.stage))
    prepared = owner.verify_source(source, args.git)
    record = owner.jsonio.read_json(stage / profile['manifest'])
    owner.require(isinstance(record, dict) and record.get('format') == profile['format']
                  and record.get('version') == 1 and record.get('target') == target,
                  'invalid freestanding builtins manifest')
    owner.require(record.get('llvm_version') == prepared['llvm_version'] and
                  record.get('source') == prepared['source'] and
                  record.get('recipe_files') == prepared['recipe']['files'],
                  'freestanding builtins source or recipe changed')
    owner.require(record.get('producer_sha256') == owner.inventory.sha256_file(__file__),
                  'freestanding builtins producer changed')
    owner.require(record.get('files') == stage_rows(owner, stage, profile), 'freestanding builtins stage changed')
    return record


def build(owner, args, target):
    profile = PROFILES[target]
    from emberbsd_sdk import host_prefix, native_checks
    source = Path(owner.paths.canonical_existing(args.source))
    prepared = owner.verify_source(source, args.git)
    owner.require(args.jobs > 0, 'jobs must be positive')
    work, stage = Path(args.work), Path(args.stage)
    for output in (work, stage):
        owner.require(output.is_absolute() and not os.path.lexists(output),
                      'select an absolute new output: ' + str(output))
        owner.paths.reject_overlap(str(output), str(source))
        owner.paths.reject_overlap(str(output), str(args.host_prefix))
    owner.paths.reject_overlap(str(work), str(stage))
    roles = ('cc', 'cxx', 'ar', 'ranlib', 'nm', 'cmake', 'ninja', 'python', 'sh', 'llvm-config', profile['linker'])
    native = host_prefix.load_host_prefix(args.host_prefix, compiler_family='clang', required_roles=roles)
    owner.require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
                  'use the selected native Python')
    owner.require(native.compiler['version'] == prepared['llvm_version'],
                  'native compiler and common runtime source versions differ')
    environment = owner.process.sanitized_environment()
    environment['PATH'] = native.path
    version = owner.process.capture([native.tool('llvm-config'), '--version'], env=environment).stdout.decode().strip()
    owner.require(version == prepared['llvm_version'], 'native LLVM and runtime source versions differ')
    work.mkdir()
    stage.mkdir()
    (work / 'sysroot').mkdir()
    (work / 'home').mkdir()
    (work / 'tmp').mkdir()
    environment = native_checks.check_environment(native, bindings=str(work / 'native-commands'),
                                                  environment=environment)
    environment.update(HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
                       SHELL=native.tool('sh'), CONFIG_SHELL=native.tool('sh'),
                       PYTHONDONTWRITEBYTECODE='1')
    settings = {
        'CMAKE_MAKE_PROGRAM': native.tool('ninja'), 'CMAKE_BUILD_TYPE': 'Release',
        'CMAKE_SYSTEM_NAME': profile['system'], 'CMAKE_SYSTEM_PROCESSOR': profile['processor'],
        'CMAKE_TRY_COMPILE_TARGET_TYPE': 'STATIC_LIBRARY', 'CMAKE_SYSROOT': work / 'sysroot',
        'CMAKE_INSTALL_PREFIX': stage, 'CMAKE_C_COMPILER': native.tool('cc'),
        'CMAKE_CXX_COMPILER': native.tool('cxx'), 'CMAKE_ASM_COMPILER': native.tool('cc'),
        'CMAKE_C_COMPILER_TARGET': target, 'CMAKE_CXX_COMPILER_TARGET': target,
        'CMAKE_ASM_COMPILER_TARGET': target, 'CMAKE_AR': native.tool('ar'),
        'CMAKE_RANLIB': native.tool('ranlib'), 'CMAKE_NM': native.tool('nm'),
        'CMAKE_LINKER': native.tool(profile['linker']), 'LLVM_CONFIG_PATH': native.tool('llvm-config'),
        'LLVM_ENABLE_PER_TARGET_RUNTIME_DIR': 'ON', 'COMPILER_RT_BAREMETAL_BUILD': 'ON',
        'COMPILER_RT_DEFAULT_TARGET_ONLY': 'ON',
        **{'COMPILER_RT_' + name: 'OFF' for name in ('INCLUDE_TESTS', 'BUILD_SANITIZERS',
            'BUILD_XRAY', 'BUILD_LIBFUZZER', 'BUILD_PROFILE', 'BUILD_CTX_PROFILE',
            'BUILD_MEMPROF', 'BUILD_ORC', 'BUILD_GWP_ASAN')},
    }
    if profile['pic']:
        settings['COMPILER_RT_BUILTINS_ENABLE_PIC'] = 'ON'
    else:
        settings['COMPILER_RT_HAS_FPIC_FLAG'] = 'OFF'
    if profile['flags']:
        settings.update({'CMAKE_' + language + '_FLAGS': profile['flags']
                         for language in ('C', 'CXX', 'ASM')})
    cmake = native.tool('cmake')
    commands = [
        [cmake, '-S', str(source / 'compiler-rt'), '-B', str(work / 'build'), '-G', 'Ninja'] +
        ['-D' + key + '=' + str(value) for key, value in sorted(settings.items())],
        [cmake, '--build', str(work / 'build'), '--parallel', str(args.jobs), '--target', 'builtins'],
        [cmake, '--build', str(work / 'build'), '--target', 'install-builtins'],
    ]
    for command in commands:
        owner.process.run_logged(command, str(work / 'build.log'), cwd=str(work), env=environment,
                                 append=(work / 'build.log').exists(), empty_snapshot_timeout=120)
    owner.require(owner.verify_source(source, args.git) == prepared, 'common runtime source changed during build')
    licenses = stage / 'share/licenses/compiler-rt'
    licenses.mkdir(parents=True)
    for relative in ('LICENSE.TXT', 'CREDITS.TXT', 'lib/builtins/LICENSE.EmberBSD-BINARY128.TXT',
                     'lib/profile/LICENSE.EmberBSD-GCOV.TXT'):
        shutil.copyfile(source / 'compiler-rt' / relative, licenses / Path(relative).name)
    record = {'format': profile['format'], 'version': 1, 'target': target,
              'llvm_version': prepared['llvm_version'], 'source': prepared['source'],
              'recipe_files': prepared['recipe']['files'],
              'producer_sha256': owner.inventory.sha256_file(__file__),
              'files': stage_rows(owner, stage, profile)}
    owner.jsonio.write_json(stage / profile['manifest'], record)
    return verify(owner, args, target)
