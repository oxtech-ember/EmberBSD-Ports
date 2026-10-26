# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Canonical CMake phases for one common LLVM target runtime implementation."""
from collections import defaultdict, deque
import os
import posixpath
from pathlib import Path
import shlex
import shutil
import sys
from types import SimpleNamespace


PROFILES = {'builtins': ['builtins'], 'bootstrap': ['builtins', 'libunwind-static'],
            'full': ['builtins', 'libunwind', 'libcxxabi', 'libcxx']}


def base_inputs(owner, root, os_source, git, full):
    owner.paths.real_directory(root / 'usr/include')
    for name in ('sys/param.h', 'stdint.h', 'limits.h'):
        owner.inventory.required_file(str(root), 'usr/include/' + name)
    if full:
        for name in ('libc.so', 'libc.a', 'crt0.o', 'crti.o', 'crtbegin.o', 'crtend.o', 'crtn.o'):
            owner.inventory.required_file(str(root), 'usr/lib/' + name)
    rows = owner.inventory.snapshot_tree(str(root))
    children = defaultdict(list)
    for name, row in rows.items():
        children[posixpath.dirname(name)].append((name, row))
    selected = {name: row for name, row in rows.items()
                if name.startswith('usr/include/') or (full and name.startswith('usr/lib/'))}
    # Include every link hop and its final bytes. In an OS sysroot, for
    # example, usr/lib/libc.so can resolve into the separate /lib directory.
    queue = deque(selected)
    while queue:
        name = queue.popleft()
        pending = name.split('/')
        prefix, hops = [], 0
        while pending:
            prefix.append(pending.pop(0))
            current = '/'.join(prefix)
            row = rows.get(current)
            owner.require(row is not None, 'base input link target is absent: ' + current)
            if row['kind'] == 'link':
                selected[current] = row
                target = posixpath.normpath(posixpath.join(posixpath.dirname(current), row['target']))
                owner.require(not target.startswith('/') and target != '..' and not target.startswith('../'),
                              'base input link escapes its sysroot')
                pending = target.split('/') + pending
                prefix = []
                hops += 1
                owner.require(hops < 40, 'base input symlink cycle')
            elif not pending:
                selected[current] = row
                if row['kind'] == 'directory':
                    for child, entry in children[current]:
                        if child not in selected:
                            selected[child] = entry
                            queue.append(child)
    return dict(os_revision=owner.git_revision(git, os_source),
                files={name: row['sha256'] for name, row in selected.items() if row['kind'] == 'file'},
                symlinks={name: row['target'] for name, row in selected.items() if row['kind'] == 'link'})


def cmake_arguments(source, work, stage, base, native, compiler, definition, version, phase):
    """Keep host programs and target ABI/compiler inputs separate."""
    root = source / ('compiler-rt/lib/builtins' if phase == 'builtins' else 'runtimes')
    arguments = [native.tool('cmake'), '-S', str(root), '-B', str(work), '-G', 'Ninja']
    settings = dict(
        CMAKE_MAKE_PROGRAM=native.tool('ninja'),
        CMAKE_BUILD_TYPE='Release', CMAKE_SYSTEM_NAME='NetBSD',
        CMAKE_SYSTEM_PROCESSOR=definition['arch'], CMAKE_SYSROOT=str(base),
        CMAKE_INSTALL_PREFIX='/usr/pkg/llvm', CMAKE_INSTALL_LIBDIR='lib',
        CMAKE_EXPORT_COMPILE_COMMANDS='ON',
        CMAKE_INSTALL_RPATH='/usr/pkg/llvm/lib', CMAKE_POSITION_INDEPENDENT_CODE='ON',
        CMAKE_C_COMPILER=compiler['binaries']['cc']['selected_path'],
        CMAKE_CXX_COMPILER=compiler['binaries']['cxx']['selected_path'],
        CMAKE_ASM_COMPILER=compiler['binaries']['cc']['selected_path'],
        CMAKE_AR=compiler['binaries']['ar']['selected_path'],
        CMAKE_RANLIB=compiler['binaries']['ranlib']['selected_path'],
        CMAKE_NM=compiler['binaries']['nm']['selected_path'],
        CMAKE_STRIP=compiler['binaries']['strip']['selected_path'],
        CMAKE_LINKER=compiler['binaries']['ld']['selected_path'],
        CMAKE_C_COMPILER_TARGET=definition['triplet'],
        CMAKE_CXX_COMPILER_TARGET=definition['triplet'],
        CMAKE_ASM_COMPILER_TARGET=definition['triplet'],
        CMAKE_FIND_ROOT_PATH=str(base), CMAKE_FIND_ROOT_PATH_MODE_PROGRAM='NEVER',
        CMAKE_FIND_ROOT_PATH_MODE_LIBRARY='ONLY', CMAKE_FIND_ROOT_PATH_MODE_INCLUDE='ONLY',
        CMAKE_FIND_ROOT_PATH_MODE_PACKAGE='ONLY',
        CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH='OFF', CMAKE_FIND_USE_CMAKE_SYSTEM_PATH='OFF',
        CMAKE_PROGRAM_PATH=native.path.replace(os.pathsep, ';'),
        Python3_EXECUTABLE=native.tool('python'), PYTHON_EXECUTABLE=native.tool('python'),
        LLVM_ENABLE_PER_TARGET_RUNTIME_DIR='OFF', LLVM_INCLUDE_TESTS='OFF',
        LLVM_INCLUDE_DOCS='OFF', LLVM_INCLUDE_BENCHMARKS='OFF',
        LLVM_ENABLE_PROJECTS='', LLVM_ENABLE_RUNTIMES='',
    )
    linker = '--ld-path=' + compiler['binaries']['ld']['selected_path']
    # Driver queries and compile-only feature probes also consume these flags.
    # Scope unused-argument suppression to link options, never all diagnostics.
    driver_flags = ['--no-default-config', '--start-no-unused-arguments',
                    linker, '--end-no-unused-arguments']
    for language in ('C', 'CXX', 'ASM'):
        settings['CMAKE_' + language + '_FLAGS'] = shlex.join(driver_flags)
    if phase != 'full':
        # The first libc is not present yet. These phases produce only archives.
        settings['CMAKE_TRY_COMPILE_TARGET_TYPE'] = 'STATIC_LIBRARY'
    if phase == 'builtins':
        settings.update(LLVM_CMAKE_DIR=native.bundle_root + '/lib/cmake/llvm',
            LLVM_DIR=native.bundle_root + '/lib/cmake/llvm', LLVM_OMIT_EXPORTS_FROM_CONFIG='ON',
            COMPILER_RT_DEFAULT_TARGET_ONLY='ON', COMPILER_RT_OS_DIR='netbsd',
            COMPILER_RT_BUILD_CRT='OFF',
            COMPILER_RT_INSTALL_PATH='lib/clang/' + version.split('.')[0],
            COMPILER_RT_BUILTINS_ENABLE_PIC='ON', COMPILER_RT_INCLUDE_TESTS='OFF')
    else:
        resource = stage / 'usr/pkg/llvm/lib/clang' / version.split('.')[0]
        # Compiler queries made by the common CMake modules also use CXX_FLAGS.
        # Keep compiler-owned headers from the selected native Clang when the
        # target resource directory contains only freshly built runtimes.
        compile_flags = shlex.join(driver_flags + ['-resource-dir=' + str(resource),
            '-nobuiltininc', '-isystem', compiler['resource_dir'] + '/include',
            '--start-no-unused-arguments', '--rtlib=compiler-rt', '--unwindlib=none',
            '--end-no-unused-arguments'])
        for language in ('C', 'CXX', 'ASM'):
            settings['CMAKE_' + language + '_FLAGS'] = compile_flags
        settings['CMAKE_CXX_FLAGS'] += ' -nostdlib++'
        link_flags = [linker, '--rtlib=compiler-rt',
                      '--unwindlib=none', '-L' + str(stage / 'usr/pkg/llvm/lib')]
        for kind in ('EXE', 'SHARED', 'MODULE'):
            settings['CMAKE_' + kind + '_LINKER_FLAGS'] = shlex.join(link_flags)
        # Installed native LLVMConfig can inject native library output paths.
        # Runtime projects use the common prepared source CMake modules instead.
        settings.update(CMAKE_DISABLE_FIND_PACKAGE_LLVM='ON', CMAKE_DISABLE_FIND_PACKAGE_Clang='ON',
            LLVM_BINARY_DIR=str(work), LLVM_DEFAULT_TARGET_TRIPLE=definition['triplet'],
            LLVM_ENABLE_RUNTIMES='libunwind' if phase == 'bootstrap' else 'libunwind;libcxxabi;libcxx',
            LIBUNWIND_ENABLE_STATIC='ON', LIBUNWIND_ENABLE_SHARED='OFF' if phase == 'bootstrap' else 'ON',
            LIBUNWIND_ENABLE_FRAME_APIS='OFF', LIBUNWIND_USE_FRAME_HEADER_CACHE='OFF',
            LIBUNWIND_ENABLE_THREADS='ON', LIBUNWIND_USE_COMPILER_RT='ON',
            LIBUNWIND_INCLUDE_TESTS='OFF', LIBUNWIND_INCLUDE_DOCS='OFF')
        if phase == 'full':
            settings.update(LIBCXX_ENABLE_STATIC='ON', LIBCXX_ENABLE_SHARED='ON',
                LIBCXXABI_ENABLE_STATIC='ON', LIBCXXABI_ENABLE_SHARED='ON',
                LIBCXXABI_USE_COMPILER_RT='ON', LIBCXXABI_USE_LLVM_UNWINDER='ON',
                LIBCXX_USE_COMPILER_RT='ON', LIBCXX_CXX_ABI='libcxxabi',
                LIBCXX_STATICALLY_LINK_ABI_IN_STATIC_LIBRARY='ON',
                LIBCXX_INCLUDE_TESTS='OFF', LIBCXXABI_INCLUDE_TESTS='OFF',
                LIBCXX_INCLUDE_BENCHMARKS='OFF', LIBCXX_INCLUDE_DOCS='OFF',
                LIBCXXABI_INCLUDE_DOCS='OFF')
    return arguments + ['-D' + key + '=' + str(value) for key, value in sorted(settings.items())]


def execute(owner, argv, work, environment, log):
    """Reuse SDK logging, signal handling and owned-process cleanup."""
    return owner.process.run_logged(argv, str(log), cwd=str(work), env=environment,
                                    append=log.exists(), empty_snapshot_timeout=120)


def artifacts(owner, stage, phase):
    prefix = stage / 'usr/pkg/llvm'

    def unique(pattern):
        matches = [p for p in prefix.rglob(pattern) if p.is_file() and not p.is_symlink()]
        owner.require(len(matches) == 1, 'expected one installed runtime artifact: ' + pattern)
        return str(matches[0].relative_to(stage))

    result = dict(builtins=unique('libclang_rt.builtins-*.a'))
    if phase != 'builtins':
        result['libunwind'] = dict(static=unique('libunwind.a'))
    if phase == 'full':
        for component, basename in (('libunwind', 'libunwind'), ('libcxxabi', 'libc++abi'), ('libcxx', 'libc++')):
            result[component] = dict(static=unique(basename + '.a'), shared=unique(basename + '.so.*'))
        result['cxx_headers'] = 'usr/pkg/llvm/include/c++/v1'
        owner.inventory.required_file(str(stage), result['cxx_headers'] + '/vector')
    return result


def inspect_inputs(owner, args, prepared):
    from emberbsd_sdk import host_prefix, llvm_runtime, target_toolchain, targets
    source = Path(owner.paths.build_path(owner.paths.canonical_new(args.source)))
    definition = targets.target_definition(args.target)
    base = Path(owner.paths.canonical_existing(args.sysroot))
    work, stage = Path(args.work), Path(args.stage)
    owner.require(args.jobs > 0 and work.is_absolute() and stage.is_absolute(), 'use absolute work/stage and positive jobs')
    for output in (work, stage):
        owner.require(not os.path.lexists(output), 'runtime output already exists: ' + str(output))
        for read_root in (source, base, Path(args.host_prefix), Path(args.target_prefix)):
            owner.paths.reject_overlap(str(output), str(read_root))
    owner.paths.reject_overlap(str(work), str(stage))
    native = host_prefix.load_host_prefix(args.host_prefix, compiler_family=args.host_compiler_family,
        required_roles=('cc', 'cxx', 'cmake', 'ninja', 'python', 'sh', 'llvm-config'))
    owner.require(owner.paths.canonical_existing(sys.executable) ==
                  owner.paths.canonical_existing(native.tool('python')),
                  'run the runtime producer with the selected native Python')
    environment = owner.process.sanitized_environment()
    environment['PATH'] = native.path
    compiler = target_toolchain.clang_compiler(args.target_prefix, definition['triplet'], host=dict(native.host), env=environment)
    owner.require(compiler['version'] == prepared['llvm_version'], 'runtime source and target Clang versions differ')
    llvm_version = owner.process.capture([native.tool('llvm-config'), '--version'],
        env=environment).stdout.decode().strip()
    owner.require(llvm_version == prepared['llvm_version'], 'native LLVM and runtime source versions differ')
    owner.inventory.required_file(native.bundle_root, 'lib/cmake/llvm/LLVMConfig.cmake')
    recipe = effective_recipe(owner, prepared, args.git)
    context = base_inputs(owner, base, args.os_source, args.git, args.phase == 'full')
    bootstrap = bootstrap_root = None
    if args.phase == 'full':
        owner.require(args.bootstrap_stage is not None, 'full runtime requires the completed bootstrap stage')
        bootstrap_root = Path(owner.paths.canonical_existing(args.bootstrap_stage))
        bootstrap = llvm_runtime.validate_stage(bootstrap_root, target=args.target,
            required_components=PROFILES['bootstrap'], base=base)
        owner.require(bootstrap['source'] == {k: prepared['source'][k] for k in ('archive', 'sha512')} and
                      bootstrap['recipe']['files'] == recipe['files'],
                      'bootstrap runtime source or recipe inputs differ')
    return SimpleNamespace(definition=definition, base=base, work=work, stage=stage,
        native=native, environment=environment, compiler=compiler, recipe=recipe,
        context=context, bootstrap=bootstrap, bootstrap_root=bootstrap_root)


def build(owner, args):
    from emberbsd_sdk import llvm_runtime, target_toolchain
    source = Path(owner.paths.canonical_existing(args.source))
    prepared = owner.verify_source(source, args.git)
    selected = inspect_inputs(owner, args, prepared)
    definition, base = selected.definition, selected.base
    work, stage = selected.work, selected.stage
    native, environment = selected.native, selected.environment
    compiler, recipe, context = selected.compiler, selected.recipe, selected.context
    bootstrap, bootstrap_root = selected.bootstrap, selected.bootstrap_root
    work.mkdir()
    stage.mkdir()
    if bootstrap is not None:
        shutil.copytree(bootstrap_root / 'usr', stage / 'usr', symlinks=True)
    for name in ('home', 'tmp'):
        (work / name).mkdir()
    environment.update(HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
                       CONFIG_SHELL=native.tool('sh'), SHELL=native.tool('sh'))
    phases = ['full'] if args.phase == 'full' else ['builtins'] + (['bootstrap'] if args.phase == 'bootstrap' else [])
    for phase in phases:
        build_dir = work / phase
        command = cmake_arguments(source, build_dir, stage, base, native, compiler, definition, prepared['llvm_version'], phase)
        execute(owner, command, work, environment, work / (phase + '.log'))
        execute(owner, [native.tool('cmake'), '--build', str(build_dir), '--parallel', str(args.jobs)] +
                (['--target', 'builtins'] if phase == 'builtins' else []),
                work, environment, work / (phase + '.log'))
        install = [native.tool('cmake'), '--build', str(build_dir), '--target', 'install-builtins'] if phase == 'builtins' else [native.tool('cmake'), '--install', str(build_dir)]
        execute(owner, install, work,
                dict(environment, DESTDIR=str(stage)), work / (phase + '.log'))
    owner.require(base_inputs(owner, base, args.os_source, args.git, args.phase == 'full') == context,
                  'base headers or libraries changed during runtime build')
    owner.require(owner.verify_source(source, args.git) == prepared,
                  'prepared LLVM source changed during runtime build')
    owner.require(target_toolchain.clang_compiler(args.target_prefix, definition['triplet'],
        host=dict(native.host), env=environment) == compiler, 'target compiler changed during runtime build')
    if bootstrap is not None:
        owner.require(llvm_runtime.validate_stage(bootstrap_root, target=args.target,
            required_components=PROFILES['bootstrap'], base=base) == bootstrap,
            'bootstrap runtime changed during full build')
        builtins = bootstrap['artifacts']['builtins']
        owner.require(owner.inventory.sha256_file(stage / builtins) == bootstrap['files'][builtins],
                      'full runtime changed reused compiler-rt builtins')
    owner.require(effective_recipe(owner, prepared, args.git)['files'] == recipe['files'],
                  'runtime producer changed during build')
    install_licenses(source, stage, args.phase)
    if args.phase == 'full':
        link_checks(owner, work, stage, base, native, compiler, definition, environment)
    rows = owner.inventory.snapshot_tree(str(stage), machine=definition['elf'])
    installed = artifacts(owner, stage, args.phase)
    if args.phase == 'builtins':
        owner.require(all(row['kind'] == 'directory' or name == installed['builtins'] or
            name.startswith('usr/pkg/llvm/share/licenses/compiler-rt/') for name, row in rows.items()),
            'unexpected file or link in builtins-only installation')
    record = dict(format='emberbsd-llvm-runtime', version=1, compiler_family='clang',
        llvm_version=prepared['llvm_version'], components=PROFILES[args.phase], target=args.target,
        triplet=definition['triplet'], machine_arch=definition['arch'], elf_machine=definition['elf'],
        prefix='usr/pkg/llvm', source={k: prepared['source'][k] for k in ('archive', 'sha512')},
        recipe=recipe, base=context, artifacts=installed,
        files={name: row['sha256'] for name, row in rows.items() if row['kind'] == 'file'},
        symlinks={name: row['target'] for name, row in rows.items() if row['kind'] == 'link'})
    if bootstrap is not None:
        consumed = [bootstrap['artifacts']['builtins'], bootstrap['artifacts']['libunwind']['static']]
        record['bootstrap'] = dict(manifest_sha256=owner.inventory.sha256_file(bootstrap_root / 'runtime.json'),
                                  files={name: bootstrap['files'][name] for name in consumed})
    manifest = stage / 'runtime.json'
    try:
        owner.jsonio.write_json(manifest, record)
        llvm_runtime.validate_stage(stage, target=args.target, required_components=PROFILES[args.phase])
    except BaseException:
        if manifest.exists():
            manifest.unlink()
        raise
    return record


def effective_recipe(owner, prepared, git):
    files = dict(prepared['recipe']['files'])
    for path in (Path(__file__).resolve(), Path(__file__).with_name('runtime.py').resolve(),
                 owner.OWNER / 'tests/runtime-c.c', owner.OWNER / 'tests/runtime-cxx.cpp'):
        files[str(path.relative_to(owner.PORTS))] = owner.inventory.sha256_file(path)
    return dict(ports_revision=owner.git_revision(git, owner.PORTS), files=files)


def install_licenses(source, stage, phase):
    components = ['compiler-rt']
    if phase != 'builtins':
        components.append('libunwind')
    if phase == 'full':
        components += ['libcxx', 'libcxxabi']
    root = stage / 'usr/pkg/llvm/share/licenses'
    for component in components:
        destination = root / component
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / component / 'LICENSE.TXT', destination / 'LICENSE.TXT')
    for name in ('CREDITS.TXT', 'lib/builtins/LICENSE.EmberBSD-BINARY128.TXT',
                 'lib/profile/LICENSE.EmberBSD-GCOV.TXT'):
        shutil.copyfile(source / 'compiler-rt' / name, root / 'compiler-rt' / Path(name).name)


def link_checks(owner, work, stage, base, native, compiler, definition, environment):
    """Link actual C and C++ consumers; execution belongs to a matching target."""
    from emberbsd_sdk.elf import read_elf_dynamic
    prefix = stage / 'usr/pkg/llvm'
    resource = prefix / 'lib/clang' / compiler['version'].split('.')[0]
    common = ['--no-default-config', '--sysroot=' + str(base), '-resource-dir=' + str(resource),
              '-nobuiltininc', '-isystem', compiler['resource_dir'] + '/include',
              '--rtlib=compiler-rt', '--unwindlib=libunwind', '-L' + str(prefix / 'lib')]
    cxx = ['-std=c++17', '-stdlib=libc++', '-nostdinc++', '-isystem',
           str(prefix / 'include/c++/v1'), '-pthread']
    fixture = owner.OWNER / 'tests/runtime-cxx.cpp'
    checks = [
        ('runtime-c', 'cc', ['-O1', str(owner.OWNER / 'tests/runtime-c.c')], 2),
        ('runtime-c-static', 'cc', ['-O1', '-static', str(owner.OWNER / 'tests/runtime-c.c')], 2),
        ('libruntime-smoke.so', 'cxx', cxx + ['-fPIC', '-shared', '-DEMBER_RUNTIME_DSO',
            '-Wl,-soname,libruntime-smoke.so', str(fixture)], 3),
        ('runtime-cxx', 'cxx', cxx + ['-DEMBER_RUNTIME_SHARED_CALLER', str(fixture),
            '-L' + str(work), '-lruntime-smoke', '-Wl,-rpath,$ORIGIN'], 2),
        ('runtime-cxx-static', 'cxx', cxx + ['-static', str(fixture)], 2),
    ]
    for name, role, flags, kind in checks:
        output = work / name
        rpath = [] if '-static' in flags else ['-Wl,-rpath,/usr/pkg/llvm/lib']
        command = compiler['commands'][role] + common + flags + rpath + ['-o', str(output)]
        execute(owner, command, work, environment, work / 'link-checks.log')
        dynamic = read_elf_dynamic(str(output), machine=definition['elf'])
        owner.require(dynamic['type'] in ((3,) if kind == 3 else (2, 3)),
                      'C/C++ smoke has the wrong ELF type')
        owner.require(not any('libgcc' in item or 'libstdc++' in item
                      for item in dynamic['needed']), 'C/C++ smoke linked a GCC runtime')
        if '-static' in flags:
            owner.require(not dynamic['needed'], 'static C/C++ smoke has shared dependencies')
