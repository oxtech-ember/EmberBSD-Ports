#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Reproduce CMake CACHE PATH conversion and inspect real DESTDIR installation.

The exact compiler-rt path declarations are evaluated by native CMake. The
installed marker is only a path fixture, never a target runtime archive.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'host-prefix', 'source', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir()
    owner_path = Path(__file__).resolve().parents[1] / 'files'
    sys.path.insert(0, str(owner_path.parent.parent / 'llvm/files'))
    import sdk_source
    sdk_source.load_sdk(['--sdk-source', str(args.sdk_source.resolve())])
    from emberbsd_sdk import host_prefix, process
    native = host_prefix.load_host_prefix(str(args.host_prefix.resolve()),
        required_roles=('cc', 'cmake', 'gmake', 'python', 'sh'))
    environment = process.sanitized_environment()
    environment['PATH'] = native.path
    triple_result = subprocess.run([native.tool('cc'), '-dumpmachine'], env=environment,
        text=True, capture_output=True)
    assert triple_result.returncode == 0, triple_result.stderr
    native_triple = triple_result.stdout.strip()
    assert native_triple and '\n' not in native_triple, native_triple
    native_arch = {'x86_64': 'amd64', 'aarch64': 'aarch64', 'i386': 'i386',
        'i486': 'i386', 'i586': 'i386', 'i686': 'i386'}.get(native_triple.split('-', 1)[0])
    assert native_arch, 'add compiler-rt host-arch mapping for ' + native_triple
    resource_result = subprocess.run([native.tool('cc'), '--print-resource-dir'],
        env=environment, text=True, capture_output=True)
    link_result = subprocess.run([native.tool('cc'), '-###', '-fsanitize=address',
        '-x', 'c', '/dev/null', '-o', '/dev/null'], env=environment,
        text=True, capture_output=True)
    assert resource_result.returncode == link_result.returncode == 0, (
        resource_result.stderr, link_result.stderr)
    resource_dir = Path(resource_result.stdout.strip())
    runtime_archives = re.findall(
        r'"([^"\n]*libclang_rt\.asan(?:_static)?\.a)"',
        link_result.stdout + link_result.stderr)
    assert resource_dir.is_absolute() and runtime_archives, link_result.stderr
    runtime_dirs = {Path(archive).parent for archive in runtime_archives}
    assert len(runtime_dirs) == 1, runtime_dirs
    runtime_dir = runtime_dirs.pop()
    assert runtime_dir.is_absolute() and runtime_dir.parent == resource_dir / 'lib', runtime_dir
    runtime_subdir = runtime_dir.relative_to(resource_dir)
    source = args.source.resolve()
    text = (source / 'compiler-rt/cmake/base-config-ix.cmake').read_text()
    declaration = re.search(r'  set\(COMPILER_RT_INSTALL_PATH "" CACHE PATH\n[^\n]+\)', text)
    paths = re.search(r'if\(LLVM_ENABLE_PER_TARGET_RUNTIME_DIR AND NOT APPLE\).*?\nendif\(\)', text, re.S)
    toolchain_dirs = (source / 'cmake/Modules/GetToolchainDirs.cmake').read_text()
    runtime_utils = (source / 'compiler-rt/cmake/Modules/CompilerRTUtils.cmake').read_text()

    def function_body(contents, name):
        found = re.search(r'(?ms)^function\(' + re.escape(name) + r'\b.*?^endfunction\(\)', contents)
        assert found, 'common compiler-rt function changed: ' + name
        return found[0]

    target_layout = function_body(toolchain_dirs, 'get_runtimes_target_libdir_common')
    get_target = function_body(runtime_utils, 'get_compiler_rt_target')
    get_install_dir = function_body(runtime_utils, 'get_compiler_rt_install_dir')
    assert declaration and paths, 'common compiler-rt install-path declarations changed'
    project = work / 'project'
    project.mkdir()
    marker = project / 'marker.txt'
    marker.write_text('only a CMake install-path fixture\n')
    (project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(RuntimeInstallPath NONE)\n'
        f'include([==[{source / "cmake/Modules/ExtendPath.cmake"}]==])\n'
        + declaration[0] + '\n' + paths[0] + '\n'
        'install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/marker.txt"\n'
        '  DESTINATION "${COMPILER_RT_INSTALL_LIBRARY_DIR}")\n')

    def run(label, argv, env):
        result = subprocess.run(argv, cwd=work, env=env, text=True, capture_output=True)
        (work / (label + '.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, (label, result.stdout, result.stderr)

    for name in ('baseline', 'selected'):
        build, stage = work / (name + '-build'), work / (name + '-stage')
        run(name + '-configure', [native.tool('cmake'), '-S', str(project), '-B', str(build),
            '-G', 'Unix Makefiles', '-DCMAKE_MAKE_PROGRAM=' + native.tool('gmake'),
            '-DCMAKE_INSTALL_PREFIX=/usr/pkg/llvm',
            '-DCOMPILER_RT_INSTALL_PATH=' + ('lib/clang/23' if name == 'baseline'
                else '/usr/pkg/llvm/lib/clang/23'),
            '-DCOMPILER_RT_OS_DIR=netbsd',
            '-DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=OFF'], environment)
        run(name + '-install', [native.tool('cmake'), '--install', str(build)],
            dict(environment, DESTDIR=str(stage)))
        expected = stage / 'usr/pkg/llvm/lib/clang/23/lib/netbsd/marker.txt'
        installed = list(stage.rglob('marker.txt'))
        assert len(installed) == 1 and installed[0].read_bytes() == marker.read_bytes()
        if name == 'baseline':
            assert not expected.exists(), 'relative CACHE PATH unexpectedly installed correctly'
            assert installed[0] == stage / str(work).lstrip('/') / 'lib/clang/23/lib/netbsd/marker.txt'
        else:
            assert installed == [expected], installed

    # Exercise the native compiler-rt consumer path as well. These are the
    # actual upstream triple mapping and install-dir functions, not a copied
    # path formula. The selected Clang supplies its triple and runtime lookup.
    native_project = work / 'native-project'
    native_project.mkdir()
    (native_project / 'marker.txt').write_bytes(marker.read_bytes())
    (native_project / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(NativeRuntimeInstallPath NONE)\n'
        f'include([==[{source / "cmake/Modules/ExtendPath.cmake"}]==])\n'
        + declaration[0] + '\n' + paths[0] + '\n' + target_layout + '\n'
        + get_target + '\n' + get_install_dir + '\n'
        f'set(COMPILER_RT_DEFAULT_TARGET_TRIPLE {native_triple})\n'
        'set(COMPILER_RT_DEFAULT_TARGET_ONLY OFF)\n'
        f'get_compiler_rt_install_dir({native_arch} runtime_install_dir)\n'
        'install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/marker.txt"\n'
        '  DESTINATION "${runtime_install_dir}")\n')
    native_cases = (
        ('native-baseline', 'lib/clang/23', 'OFF',
         work / 'native-baseline-build', work / 'native-baseline-stage'),
        ('native-selected', '/usr/pkg/llvm/lib/clang/23', 'ON',
         work / 'native-selected-build', work / 'native-selected-stage'),
    )
    for label, install_path, per_target, build, stage in native_cases:
        configure = [native.tool('cmake'), '-S', str(native_project), '-B', str(build),
            '-G', 'Unix Makefiles', '-DCMAKE_MAKE_PROGRAM=' + native.tool('gmake'),
            '-DCMAKE_INSTALL_PREFIX=/usr/pkg/llvm', '-DCMAKE_SYSTEM_NAME=Linux',
            '-DCOMPILER_RT_INSTALL_PATH=' + install_path,
            '-DCOMPILER_RT_OS_DIR=linux',
            '-DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=' + per_target]
        run(label + '-configure', configure, environment)
        run(label + '-install', [native.tool('cmake'), '--install', str(build)],
            dict(environment, DESTDIR=str(stage)))
        installed = list(stage.rglob('marker.txt'))
        assert len(installed) == 1 and installed[0].read_bytes() == marker.read_bytes()
        expected = stage / 'usr/pkg/llvm/lib/clang/23' / runtime_subdir / 'marker.txt'
        if label == 'native-baseline':
            assert installed[0] == stage / str(work).lstrip('/') / 'lib/clang/23/lib/linux/marker.txt'
            assert not expected.exists(), 'baseline unexpectedly selected native triple layout'
        else:
            assert installed == [expected], installed
    print('PASS: real CMake reproduces target and native CACHE PATH failures; selected Linux install matches Clang triple lookup')


if __name__ == '__main__':
    main()
