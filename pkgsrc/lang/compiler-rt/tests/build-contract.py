#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Test native/target routing and actual immutable base link closure."""
import argparse
import importlib.util
from pathlib import Path
import shlex
from types import SimpleNamespace


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--sdk-source', required=True)
    cli.add_argument('--work', type=Path, required=True)
    args = cli.parse_args()
    args.work.mkdir()
    files = Path(__file__).resolve().parents[1] / 'files'
    owner = module(files / 'source.py', 'runtime_source')
    owner.load_sdk(['--sdk-source', args.sdk_source])
    producer = module(files / 'build.py', 'runtime_builder')
    from emberbsd_sdk.targets import target_definition

    native = SimpleNamespace(tool=lambda role: '/native/bin/' + role,
                             path='/native/bin:/native/sbin', bundle_root='/native')
    compiler = dict(resource_dir='/target/lib/clang/23', binaries={
        role: dict(selected_path='/target/bin/' + name)
        for role, name in [('cc', 'clang'), ('cxx', 'clang++'), ('ar', 'llvm-ar'),
                           ('ranlib', 'llvm-ranlib'), ('nm', 'llvm-nm'), ('strip', 'llvm-strip'), ('ld', 'ld.lld')]})
    cxx_header = '/stage/usr/pkg/llvm/include/c++/v1'
    builtin_header = '/target/lib/clang/23/include'
    for role in ('cc', 'cxx'):
        flags = producer.link_check_include_flags(Path('/stage/usr/pkg/llvm'), compiler, role)
        headers = [flags[i + 1] for i, value in enumerate(flags) if value == '-isystem']
        assert headers == ([cxx_header, builtin_header] if role == 'cxx' else [builtin_header])

    for target in ('aarch64', 'amd64'):
        definition = target_definition(target)
        for phase in ('builtins', 'bootstrap', 'full'):
            command = producer.cmake_arguments(Path('/source'), Path('/work'), Path('/stage'),
                Path('/base'), native, compiler, definition, '23.1.4', phase)
            assert command[0] == '/native/bin/cmake'
            options = dict(item[2:].split('=', 1) for item in command if item.startswith('-D'))
            assert options['LLVM_ENABLE_PER_TARGET_RUNTIME_DIR'] == 'OFF'
            assert options['CMAKE_C_COMPILER'] == '/target/bin/clang'
            assert options['CMAKE_CXX_COMPILER_TARGET'] == definition['triplet']
            assert options['CMAKE_MAKE_PROGRAM'] == '/native/bin/ninja'
            assert options['Python3_EXECUTABLE'] == '/native/bin/python'
            assert options['CMAKE_SYSROOT'] == '/base'
            assert options['CMAKE_FIND_ROOT_PATH_MODE_LIBRARY'] == 'ONLY'
            assert options['CMAKE_FIND_ROOT_PATH_MODE_PACKAGE'] == 'ONLY'
            for language in ('C', 'CXX', 'ASM'):
                flags = shlex.split(options['CMAKE_' + language + '_FLAGS'])
                assert '--no-default-config' in flags
                linker = flags.index('--ld-path=/target/bin/ld.lld')
                assert flags.index('--start-no-unused-arguments') < linker < flags.index('--end-no-unused-arguments')
                maps = [flag for flag in flags if flag.startswith('-ffile-prefix-map=')]
                assert maps == ['-ffile-prefix-map=/source=/usr/src/external/llvm',
                                '-ffile-prefix-map=/work=/usr/obj/llvm-runtime/' + phase,
                                '-ffile-prefix-map=/stage=', '-ffile-prefix-map=/base=',
                                '-ffile-prefix-map=/target/lib/clang/23=/usr/pkg/llvm/lib/clang/23'], maps
            if phase == 'builtins':
                assert options['COMPILER_RT_INSTALL_PATH'] == '/usr/pkg/llvm/lib/clang/23'
                assert options['COMPILER_RT_BUILD_CRT'] == 'OFF'
                assert options['COMPILER_RT_DEFAULT_TARGET_ONLY'] == 'ON'
            else:
                flags = shlex.split(options['CMAKE_CXX_FLAGS'])
                assert '-nostdlib++' in flags  # project() probes precede the new C++ library build
                assert '-resource-dir=/stage/usr/pkg/llvm/lib/clang/23' in flags
                assert flags[flags.index('-isystem') + 1] == '/target/lib/clang/23/include'
                assert '--ld-path=/target/bin/ld.lld' in shlex.split(options['CMAKE_EXE_LINKER_FLAGS'])
                assert options['LIBUNWIND_ENABLE_STATIC'] == 'ON'
                assert options['LIBUNWIND_ENABLE_FRAME_APIS'] == 'OFF'
                assert options['LIBUNWIND_USE_FRAME_HEADER_CACHE'] == 'OFF'
                assert options['LIBUNWIND_ENABLE_THREADS'] == 'ON'
                assert options['CMAKE_DISABLE_FIND_PACKAGE_LLVM'] == 'ON'
                assert options['CMAKE_DISABLE_FIND_PACKAGE_Clang'] == 'ON'
                assert options['LLVM_BINARY_DIR'] == '/work'
                for language in ('C', 'CXX', 'ASM'):
                    flags = shlex.split(options['CMAKE_' + language + '_FLAGS'])
                    assert '-nobuiltininc' in flags
                    assert '--rtlib=compiler-rt' in flags
                    assert '--unwindlib=none' in flags
            if phase == 'full':
                assert 'CMAKE_TRY_COMPILE_TARGET_TYPE' not in options
                assert options['LIBCXX_ENABLE_SHARED'] == options['LIBCXX_ENABLE_STATIC'] == 'ON'
                assert options['LIBCXX_HARDENING_MODE'] == 'extensive'
                assert options['LIBCXX_STATICALLY_LINK_ABI_IN_STATIC_LIBRARY'] == 'ON'
                assert options.get('LIBCXX_ENABLE_FILESYSTEM', 'ON') == 'ON'
                assert options.get('LIBCXX_ENABLE_LOCALIZATION', 'ON') == 'ON'
            else:
                assert options['CMAKE_TRY_COMPILE_TARGET_TYPE'] == 'STATIC_LIBRARY'

    root = args.work / 'base'
    for directory in ('usr/include', 'usr/lib', 'lib'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for name in ('sys/param.h', 'stdint.h', 'limits.h'):
        path = root / 'usr/include' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('/* supplied OS header */\n')
    for name in ('libc.a', 'crt0.o', 'crti.o', 'crtbegin.o', 'crtend.o', 'crtn.o'):
        (root / 'usr/lib' / name).write_bytes(b'fixture')
    (root / 'usr/lib/libc.so').symlink_to('../../lib/libc.so')
    (root / 'lib/libc.so').symlink_to('libc.so.12')
    actual = root / 'lib/libc.so.12'
    actual.write_bytes(b'original linked DSO')
    owner.git_revision = lambda git, root: 'a' * 40
    (root / 'dev').mkdir()
    (root / 'var/run').mkdir(parents=True)
    (root / 'dev/log').symlink_to('../var/run/log')
    # Runtime sockets are absent in a build sysroot and do not supply ABI bytes.
    before = producer.base_inputs(owner, root, '/os', '/git', True)
    assert 'lib/libc.so' in before['symlinks'] and 'lib/libc.so.12' in before['files']
    actual.write_bytes(b'changed linked DSO')
    after = producer.base_inputs(owner, root, '/os', '/git', True)
    assert before != after, 'resolved DSO change was not recorded'
    actual.write_bytes(b'original linked DSO')
    (root / 'lib/libc.so.13').write_bytes(b'original linked DSO')
    (root / 'lib/libc.so').unlink()
    (root / 'lib/libc.so').symlink_to('libc.so.13')
    assert before != producer.base_inputs(owner, root, '/os', '/git', True), 'link hop changed unnoticed'
    (root / 'sys/headers').mkdir(parents=True)
    header = root / 'sys/headers/arch.h'
    header.write_text('/* selected machine header */\n')
    (root / 'usr/include/machine').symlink_to('../../sys/headers')
    headers_before = producer.base_inputs(owner, root, '/os', '/git', False)
    assert 'sys/headers/arch.h' in headers_before['files']
    header.write_text('/* changed machine header */\n')
    assert headers_before != producer.base_inputs(owner, root, '/os', '/git', False)
    header_only = producer.base_inputs(owner, root, '/os', '/git', False)
    assert set(header_only['files']) == {'usr/include/sys/param.h', 'usr/include/stdint.h', 'usr/include/limits.h', 'sys/headers/arch.h'}
    for target in ('missing-header.h', '../../../outside.h'):
        link = root / 'usr/include/unusable.h'
        link.symlink_to(target)
        try:
            producer.base_inputs(owner, root, '/os', '/git', False)
        except owner.SDKError:
            pass
        else:
            raise AssertionError('unusable selected ABI link was accepted: ' + target)
        finally:
            link.unlink()
    # Resolve .. only after expanding an earlier directory symlink.
    (root / 'actual/subdir').mkdir(parents=True)
    (root / 'outside.h').write_text('decoy')
    used = root / 'actual/outside.h'
    used.write_text('actual header')
    jump = root / 'jump'
    jump.symlink_to('actual/subdir')
    alias = root / 'usr/include/alias.h'
    alias.symlink_to('../../jump/../outside.h')
    linked = producer.base_inputs(owner, root, '/os', '/git', False)
    assert 'actual/outside.h' in linked['files'] and 'outside.h' not in linked['files']
    used.write_text('changed actual header')
    assert linked != producer.base_inputs(owner, root, '/os', '/git', False)
    alias.unlink()
    jump.unlink()
    (root / 'cycle').symlink_to('cycle')
    external = args.work / 'external'
    (external / 'subdir').mkdir(parents=True)
    (external / 'outside.h').write_text('external header')
    jump.symlink_to(external / 'subdir')
    for target in ('../../missing/../outside.h', '../../cycle/../outside.h',
                   '../../jump/../outside.h'):
        alias.symlink_to(target)
        try:
            producer.base_inputs(owner, root, '/os', '/git', False)
        except owner.SDKError:
            pass
        else:
            raise AssertionError('invalid directory-link/.. traversal was accepted: ' + target)
        finally:
            alias.unlink()
    (external / 'outside.h').write_text('changed external bytes')
    alias.symlink_to('../../jump/../outside.h')
    try:
        producer.base_inputs(owner, root, '/os', '/git', False)
    except owner.SDKError:
        pass
    else:
        raise AssertionError('changed external ABI bytes were accepted')
    alias.unlink()
    jump.unlink()
    (root / 'usr/include/stdint.h').unlink()
    try:
        producer.base_inputs(owner, root, '/os', '/git', False)
    except owner.SDKError:
        pass
    else:
        raise AssertionError('missing required preliminary header was accepted')
    print('PASS: six phase/target routes with canonical file prefix maps, resolved DSO, link-hop and directory-header changes, headers-only bootstrap and directory-link parent traversal')


if __name__ == '__main__':
    main()
