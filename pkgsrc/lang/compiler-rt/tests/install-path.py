#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Reproduce CMake CACHE PATH conversion and inspect real DESTDIR installation.

The exact compiler-rt path declarations are evaluated by native CMake. The
installed marker is only a path fixture, never a target runtime archive.
"""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'host-prefix', 'source', 'work'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir()
    files = Path(__file__).resolve().parents[1] / 'files'
    owner = module(files / 'source.py', 'install_path_source')
    owner.load_sdk(['--sdk-source', str(args.sdk_source.resolve())])
    from emberbsd_sdk import host_prefix, process, target_toolchain, targets
    native = host_prefix.load_host_prefix(str(args.host_prefix.resolve()),
        required_roles=('cc', 'cxx', 'cmake', 'ninja', 'python', 'sh'))
    environment = process.sanitized_environment()
    environment['PATH'] = native.path
    definition = targets.target_definition('amd64')
    compiler = target_toolchain.clang_compiler(native.bundle_root, definition['triplet'],
        host=dict(native.host), env=environment)
    producer = module(files / 'build.py', 'install_path_builder')
    source = args.source.resolve()
    text = (source / 'compiler-rt/cmake/base-config-ix.cmake').read_text()
    declaration = re.search(r'  set\(COMPILER_RT_INSTALL_PATH "" CACHE PATH\n[^\n]+\)', text)
    paths = re.search(r'if\(LLVM_ENABLE_PER_TARGET_RUNTIME_DIR AND NOT APPLE\).*?\nendif\(\)', text, re.S)
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
        argv = producer.cmake_arguments(source, build, stage, work / 'headers',
            native, compiler, definition, '23.1.4', 'builtins')
        options = dict(item[2:].split('=', 1) for item in argv if item.startswith('-D'))
        if name == 'baseline':
            options['COMPILER_RT_INSTALL_PATH'] = 'lib/clang/23'
        selected = ('CMAKE_INSTALL_PREFIX', 'COMPILER_RT_INSTALL_PATH',
                    'COMPILER_RT_OS_DIR', 'LLVM_ENABLE_PER_TARGET_RUNTIME_DIR')
        run(name + '-configure', [native.tool('cmake'), '-S', str(project), '-B', str(build),
            '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + native.tool('ninja'),
            *['-D' + key + '=' + options[key] for key in selected]], environment)
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
    print('PASS: real CMake reproduces cwd-based CACHE PATH and installs selected target path under DESTDIR')


if __name__ == '__main__':
    main()
