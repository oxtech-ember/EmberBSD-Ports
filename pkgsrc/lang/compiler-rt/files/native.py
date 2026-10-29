#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Build the common LLVM libc++ for the selected Darwin host ABI."""
import argparse
import os
from pathlib import Path
import re
import shlex
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import source as owner


def cmake_arguments(source, work, prefix, sdk, minimum, native, bindings):
    """Keep host tools, Darwin ABI inputs, and installed runtime explicit."""
    linker = '--ld-path=' + native.tool('ld')
    flags = shlex.join(['--no-default-config', '--start-no-unused-arguments', linker,
                        '--end-no-unused-arguments'])
    settings = dict(
        CMAKE_MAKE_PROGRAM=native.tool('ninja'), CMAKE_BUILD_TYPE='Release',
        CMAKE_OSX_SYSROOT=str(sdk), CMAKE_OSX_DEPLOYMENT_TARGET=minimum,
        CMAKE_OSX_ARCHITECTURES={'arm64': 'arm64', 'aarch64': 'arm64',
                                 'x86_64': 'x86_64', 'amd64': 'x86_64'}[native.host['cpu']],
        CMAKE_INSTALL_PREFIX=str(prefix), CMAKE_INSTALL_LIBDIR='lib',
        CMAKE_INSTALL_NAME_DIR=str(prefix / 'lib/libc++'), CMAKE_INSTALL_RPATH=str(prefix / 'lib/libc++'),
        CMAKE_BUILD_WITH_INSTALL_NAME_DIR='ON', CMAKE_BUILD_WITH_INSTALL_RPATH='ON',
        CMAKE_C_COMPILER=bindings['CC'], CMAKE_CXX_COMPILER=bindings['CXX'],
        CMAKE_AR=native.tool('ar'), CMAKE_RANLIB=native.tool('ranlib'),
        CMAKE_LINKER=native.tool('ld'), CMAKE_C_FLAGS=flags, CMAKE_CXX_FLAGS=flags,
        # Match Darwin's libc++ link contract: ABI symbols are available to
        # ordinary -lc++ consumers through the selected system ABI library.
        CMAKE_SHARED_LINKER_FLAGS=shlex.join(['-Wl,-reexport_library,' + str(sdk / 'usr/lib/libc++abi.tbd')]),
        CMAKE_INSTALL_NAME_TOOL=str(prefix / 'bin/llvm-install-name-tool'),
        CMAKE_LIPO=str(prefix / 'bin/llvm-lipo'),
        CMAKE_LIBTOOL=str(prefix / 'bin/llvm-libtool-darwin'),
        CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH='OFF', CMAKE_FIND_USE_CMAKE_SYSTEM_PATH='OFF',
        CMAKE_PROGRAM_PATH=native.path.replace(os.pathsep, ';'),
        Python3_EXECUTABLE=native.tool('python'), PYTHON_EXECUTABLE=native.tool('python'),
        CMAKE_EXPORT_COMPILE_COMMANDS='ON',
        LLVM_ENABLE_RUNTIMES='libcxx', LLVM_INCLUDE_TESTS='OFF', LLVM_INCLUDE_DOCS='OFF',
        LLVM_INCLUDE_BENCHMARKS='OFF', LIBCXX_INCLUDE_TESTS='OFF',
        LIBCXX_INCLUDE_BENCHMARKS='OFF', LIBCXX_INCLUDE_DOCS='OFF',
        LIBCXX_HARDENING_MODE='extensive', LIBCXX_ABI_VERSION='1',
        LIBCXX_ABI_NAMESPACE='__ember1', LIBCXX_SHARED_OUTPUT_NAME='c++_ember1',
        LIBCXX_INSTALL_INCLUDE_DIR='include/libc++/v1',
        LIBCXX_INSTALL_INCLUDE_TARGET_DIR='include/libc++/v1',
        LIBCXX_INSTALL_LIBRARY_DIR='lib/libc++',
        LIBCXX_CXX_ABI='system-libcxxabi',
        LIBCXX_CXX_ABI_INCLUDE_PATHS=str(sdk / 'usr/include/c++/v1'),
        LIBCXX_ENABLE_SHARED='ON', LIBCXX_ENABLE_STATIC='ON',
        LIBCXX_ENABLE_FILESYSTEM='ON', LIBCXX_ENABLE_LOCALIZATION='ON',
        LIBCXX_ENABLE_EXCEPTIONS='ON', LIBCXX_ENABLE_RTTI='ON',
        LIBCXX_ENABLE_ABI_LINKER_SCRIPT='OFF')
    return [native.tool('cmake'), '-S', str(source / 'runtimes'), '-B', str(work),
            '-G', 'Ninja'] + ['-D' + key + '=' + str(value) for key, value in sorted(settings.items())]


def validate_darwin_load_commands(text, prefix):
    """Require the final selected install name and explicit platform ABI."""
    commands = []
    for block in re.split(r'(?m)^Load command [0-9]+\s*$', text):
        command = re.search(r'(?m)^\s*cmd (LC_[A-Z_]+)\s*$', block)
        name = re.search(r'(?m)^\s*name (.+?) \(offset [0-9]+\)\s*$', block)
        if command and name:
            commands.append((command.group(1), name.group(1)))
    expected = str(prefix / 'lib/libc++/libc++_ember1.1.dylib')
    owner.require([name for kind, name in commands if kind == 'LC_ID_DYLIB'] == [expected],
                  'native libc++ install name differs from selected prefix')
    owner.require(('LC_REEXPORT_DYLIB', '/usr/lib/libc++abi.dylib') in commands,
                  'native libc++ does not re-export the selected system ABI')
    allowed = {'/usr/lib/libc++abi.dylib', '/usr/lib/libSystem.B.dylib'}
    deps = [name for kind, name in commands if kind in
            ('LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB', 'LC_LOAD_UPWARD_DYLIB')]
    owner.require(set(deps) == allowed, 'native libc++ has unexpected load dependencies')


def main(arguments):
    arguments = owner.load_sdk(arguments)
    from emberbsd_sdk import host_prefix, native_checks
    from emberbsd_sdk.errors import SDKError
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'host-prefix', 'macos-sdk', 'macos-minimum', 'work', 'stage'):
        cli.add_argument('--' + name, required=True)
    cli.add_argument('--pkgsrc-root', help='explicit exported pkgsrc root')
    cli.add_argument('--git', help='absolute Git for a Ports checkout')
    cli.add_argument('--jobs', type=int, default=1)
    args = cli.parse_args(arguments)
    try:
        owner.select_recipe_root(args.pkgsrc_root)
        prefix = Path(owner.paths.canonical_existing(args.host_prefix))
        sdk = Path(owner.paths.canonical_existing(args.macos_sdk))
        source = Path(owner.paths.canonical_existing(args.source))
        work, stage = Path(args.work), Path(args.stage)
        owner.require(args.jobs > 0 and re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', args.macos_minimum),
                      'invalid job count or macOS deployment target')
        for output in (work, stage):
            owner.require(output.is_absolute() and not os.path.lexists(output), 'output must be new and absolute')
            for input_root in (prefix, sdk, source): owner.paths.reject_overlap(str(output), str(input_root))
        owner.paths.reject_overlap(str(work), str(stage))
        native = host_prefix.load_host_prefix(str(prefix), compiler_family='clang',
            required_roles=('cc', 'cxx', 'ld', 'ar', 'ranlib', 'cmake', 'ninja', 'python', 'sh', 'objdump'))
        owner.require(native.host['os'] == 'Darwin', 'native runtime producer currently requires Darwin')
        owner.require(Path(sys.executable).resolve() == Path(native.tool('python')).resolve(),
                      'run with selected native Python')
        for name in ('llvm-install-name-tool', 'llvm-lipo', 'llvm-libtool-darwin'):
            path = (prefix / 'bin' / name).resolve(strict=True)
            owner.require(path.is_relative_to(prefix) and path.is_file() and os.access(path, os.X_OK),
                          'selected Darwin tool is missing or outside host prefix: ' + name)
        for rel in ('usr/include/c++/v1/cxxabi.h', 'usr/include/c++/v1/__cxxabi_config.h',
                    'usr/lib/libc++abi.tbd', 'usr/lib/libSystem.tbd'):
            owner.inventory.required_file(str(sdk), rel)
        prepared = owner.verify_source(source, args.git)
        env = owner.process.sanitized_environment(); env['PATH'] = native.path
        work.mkdir(parents=True); stage.mkdir(parents=True)
        env = native_checks.check_environment(native, bindings=str(work / 'native-commands'), environment=env)
        for name in ('home', 'tmp'): (work / name).mkdir()
        env.update(HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), SDKROOT=str(sdk),
                   MACOSX_DEPLOYMENT_TARGET=args.macos_minimum, CONFIG_SHELL=native.tool('sh'),
                   SHELL=native.tool('sh'), PYTHONDONTWRITEBYTECODE='1')
        log = work / 'build.log'
        commands = [cmake_arguments(source, work / 'cmake', prefix, sdk, args.macos_minimum, native, env),
                    [native.tool('cmake'), '--build', str(work / 'cmake'), '--parallel', str(args.jobs)],
                    [native.tool('cmake'), '--install', str(work / 'cmake')]]
        for index, command in enumerate(commands):
            install_env = dict(env, DESTDIR=str(stage)) if index == 2 else env
            owner.process.run_logged(command, str(log), env=install_env, append=index != 0)
        owner.require(owner.verify_source(source, args.git) == prepared, 'runtime source changed during build')
        installed = stage / str(prefix).lstrip('/')
        config = installed / 'include/libc++/v1/__config_site'
        owner.require(config.is_file() and '#define _LIBCPP_ABI_NAMESPACE __ember1' in config.read_text() and
                      '#define _LIBCPP_HARDENING_MODE_DEFAULT 16' in config.read_text(),
                      'installed libc++ does not expose the selected ABI/hardening')
        library = installed / 'lib/libc++'
        dylib = library / 'libc++_ember1.1.dylib'
        generated_link = library / 'libc++_ember1.dylib'
        linker_link = library / 'libc++.dylib'
        owner.require(dylib.is_file() and generated_link.is_symlink() and
                      os.readlink(generated_link) == dylib.name and
                      not os.path.lexists(linker_link) and
                      not os.path.lexists(library / 'libc++.1.dylib'),
                      'unexpected native libc++ library layout')
        generated_link.unlink()
        linker_link.symlink_to(dylib.name)
        load_commands = owner.process.capture([native.tool('objdump'), '--macho', '--private-headers',
                                               str(dylib)], env=env).stdout.decode('utf-8', 'strict')
        validate_darwin_load_commands(load_commands, prefix)
        print('native Darwin libc++ EXTENSIVE stage built:', installed)
    except (SDKError, OSError, ValueError) as error:
        cli.exit(1, 'native LLVM runtime: ' + str(error) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
