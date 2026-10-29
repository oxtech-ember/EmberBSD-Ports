#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compose existing host tools without rebuilding.
import argparse
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from llvm_host import checked_paths, load_sdk, query


def prepare_gcc(compiler, os_tools, output, target):
    profile = Path(__file__).resolve().parents[2] / 'development-toolchain'
    sys.path[:0] = [str(profile), str(profile / 'cross')]
    from host import BINUTILS, TARGETS, tools_message, missing_tools
    drivers = ('gcc', 'g++', 'cpp', 'gcc-ar', 'gcc-nm', 'gcc-ranlib')
    triplet = TARGETS[target][0]
    compiler_names = drivers + tuple(BINUTILS)
    install_name = os_tools + '/bin/' + triplet + '-install'
    missing = missing_tools(compiler, triplet, compiler_names)
    if not os.access(install_name, os.X_OK):
        missing.append('install')
    if missing:
        raise ValueError(tools_message(missing, list(compiler_names) + ['install']))
    gcc = compiler + '/bin/' + triplet + '-gcc'
    if query([gcc, '-dumpmachine']) != triplet or query([gcc, '-dumpfullversion']) != '16.2.0':
        raise ValueError('Matching GCC16.2.0 target compiler required')
    tools = {name: compiler + '/bin/' + triplet + '-' + name for name in compiler_names}
    tools['install'] = install_name
    Path(output, 'bin').mkdir(parents=True)
    for name, path in tools.items():
        Path(output, 'bin', triplet + '-' + name).symlink_to(path)
    print('Prepared GCC16 cross tools with the NetBSD host install utility.')


def make_value(value):
    if any(character.isspace() or character in '\\"\'`$#;:' for character in value):
        raise ValueError('Cross make paths must not contain whitespace or make/shell metacharacters')
    return value


def prepare_clang(options):
    from emberbsd_sdk import application_toolchain, llvm_runtime, paths, process, target_toolchain
    from emberbsd_sdk.host_prefix import load_host_prefix, _member
    if application_toolchain.APPLICATION_TOOLCHAIN_API < 2:
        raise ValueError('The selected SDK must provide application toolchain API 2')
    if not options.sysroot or not options.host_prefix:
        raise ValueError('Clang applications require --sysroot and --host-prefix')
    checked_paths((options.sysroot, options.host_prefix, *([options.runtime_base] if options.runtime_base else [])))
    native = load_host_prefix(options.host_prefix, required_roles=('python', 'sh'),
        compiler_family=options.host_compiler_family)
    if Path(sys.executable).resolve() != Path(native.tool('python')).resolve():
        raise ValueError('Run the adapter with the selected host-prefix Python')
    env = process.sanitized_environment()
    env['PATH'] = native.path
    triplet = {'aarch64':'aarch64--netbsd', 'amd64':'x86_64--netbsd'}[options.target]
    compiler = target_toolchain.clang_compiler(options.compiler, triplet,
        host=native.host, env=env)
    sysroot = paths.canonical_existing(options.sysroot)
    if options.runtime_stage:
        runtime_root = paths.canonical_existing(options.runtime_stage)
        runtime_base = paths.canonical_existing(options.runtime_base or sysroot)
        runtime = llvm_runtime.validate_stage(runtime_root, target=options.target,
            required_components=llvm_runtime.FULL_COMPONENTS, base=runtime_base)
    else:
        runtime_root = runtime_base = sysroot
        runtime = application_toolchain.load_clang_runtime(sysroot, target=options.target)
    os_tools = paths.canonical_existing(options.os_tools)
    install = str(Path(os_tools, 'bin', triplet + '-install'))
    _member(install, os_tools, native.host, search_path=native.path)
    output = Path(paths.canonical_new(options.output))
    runtime_prefix = make_value(runtime['prefix'])
    libraries = sorted({str(Path(runtime['artifacts'][role]['shared']).parent)
                        for role in ('libcxx', 'libcxxabi', 'libunwind')})
    for value in (str(output), sysroot, runtime_root, runtime_base, *libraries):
        make_value(value)
    # A prepared directory is routing, not another runtime or acceptance record.
    # Refuse all input errors before creating it and remove only our new output
    # if command binding fails.
    output.mkdir()
    try:
        bound = application_toolchain.bind_clang_application_commands(
            output/'commands', compiler, sysroot, runtime,
            python=native.tool('python'), include_auxiliary=True, runtime_root=runtime_root)
        binaries = output/'bin'; binaries.mkdir()
        aliases = {'clang':bound['cc'], 'clang++':bound['cxx'], 'clang-cpp':bound['cpp']}
        aliases.update({triplet+'-'+name:path for name,path in aliases.copy().items()})
        aliases.update({triplet+'-'+role:bound[role] for role in ('as','ld')})
        aliases.update({triplet+'-'+role:row['selected_path']
            for role,row in compiler['binaries'].items()
            if role not in ('cc','cxx','cpp','as','ld')})
        aliases[triplet+'-install'] = install
        for name, path in aliases.items():
            (binaries/name).symlink_to(path)
        values = {'FAMILY':'clang', 'TARGET':options.target, 'TRIPLET':triplet,
                  'SYSROOT':sysroot, 'TOOLS':str(output), 'RUNTIME_PREFIX':runtime_prefix,
                  'RUNTIME_ROOT':runtime_root, 'RUNTIME_KIND':('stage' if options.runtime_stage else 'sysroot'),
                  'RUNTIME_VERSION':runtime['llvm_version'], 'RUNTIME_BASE':runtime_base,
                  'SDK_SOURCE':str(Path(__import__('emberbsd_sdk').__file__).resolve().parents[2]),
                  'NATIVE_PYTHON':native.tool('python'),
                  'RUNTIME_LIBRARY_PATHS':';'.join(str(Path(runtime_root, name)) for name in libraries)}
        text = '# Generated from the selected SDK compiler and runtime.\n'
        text += ''.join('_EMBER_TARGET_' + key + ':= ' + value + '\n'
                        for key,value in values.items())
        (output/'target.mk').write_text(text)
    except BaseException:
        shutil.rmtree(output)
        raise
    print('Prepared Clang application tools from the selected SDK runtime.')


def prepare(args):
    parser = argparse.ArgumentParser(description='Compose selected SDK cross tools without rebuilding.')
    parser.add_argument('--target', choices=('aarch64','amd64'), default='aarch64')
    parser.add_argument('--compiler-family', choices=('clang','gcc'), default='clang')
    parser.add_argument('--host-compiler-family', choices=('clang','gcc'), default='clang')
    parser.add_argument('--host-prefix')
    parser.add_argument('--sysroot')
    parser.add_argument('--runtime-stage', help='explicit completed LLVM runtime stage for this sysroot')
    parser.add_argument('--runtime-base', help='foundation used to build the explicit runtime stage')
    parser.add_argument('compiler', metavar='COMPILER_PREFIX')
    parser.add_argument('os_tools', metavar='OS_TOOLDIR')
    parser.add_argument('output', metavar='NEW_TOOLDIR')
    options = parser.parse_args(args)
    if options.runtime_base and not options.runtime_stage:
        raise ValueError('--runtime-base requires --runtime-stage')
    checked_paths((options.compiler, options.os_tools, options.output))
    if os.path.lexists(options.output):
        raise ValueError('Output already exists')
    if options.compiler_family == 'clang':
        prepare_clang(options)
    else:
        if options.runtime_stage:
            raise ValueError('--runtime-stage requires Clang')
        prepare_gcc(options.compiler, options.os_tools, options.output, options.target)


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        _, args = load_sdk()
        prepare(args)
    except Exception as error:
        exit_error(error)
