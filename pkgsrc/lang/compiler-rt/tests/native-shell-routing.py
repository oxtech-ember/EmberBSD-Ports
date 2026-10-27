#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise literal CMake shell lookup through the selected native tools."""
import argparse
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
FILES = Path(__file__).resolve().parents[1] / 'files'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'host-prefix', 'target-prefix', 'source'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--target', required=True)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    args.work.mkdir()
    args.work = args.work.resolve()

    source_owner = module(FILES / 'source.py', 'native_shell_source')
    source_owner.load_sdk(['--sdk-source', str(args.sdk_source.resolve())])
    from emberbsd_sdk import host_prefix, native_checks, process, target_toolchain, targets

    assert native_checks.NATIVE_CHECKS_API == 1
    native = host_prefix.load_host_prefix(str(args.host_prefix.resolve()),
        compiler_family='clang', required_roles=('cc', 'cxx', 'cpp', 'cmake',
            'ninja', 'python', 'sh', 'llvm-config'))
    assert Path(native.tool('sh')).name == 'mksh', native.tool('sh')
    for directory in native.path.split(os.pathsep):
        assert not (Path(directory) / 'sh').exists(), 'baseline PATH unexpectedly aliases sh'

    home, tmp = args.work / 'home', args.work / 'tmp'
    home.mkdir()
    tmp.mkdir()
    ambient = dict(PATH=native.path,
        HOME=str(home), TMPDIR=str(tmp), SHELL=native.tool('sh'),
        CONFIG_SHELL=native.tool('sh'), CC='/foreign/host/cc',
        CXX='/foreign/host/cxx', CPP='/foreign/host/cpp',
        CPPFLAGS='-I/foreign/host/include', CFLAGS='-isysroot /foreign/host/sdk',
        CXXFLAGS='-I/foreign/host/cxx-include', LDFLAGS='-L/foreign/host/lib')
    baseline = process.sanitized_environment(ambient)
    config_guess = args.source.resolve() / 'llvm/cmake/config.guess'
    assert config_guess.is_file(), config_guess
    try:
        subprocess.run(['sh', str(config_guess)], cwd=args.work, env=baseline,
                       check=True, capture_output=True, text=True)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('literal sh unexpectedly resolves in the unbound native PATH')

    environment = native_checks.check_environment(native,
        bindings=str(args.work / 'native-commands'), environment=ambient)
    binding_dir = Path(environment['PATH'].split(os.pathsep)[0])
    assert os.path.islink(binding_dir / 'sh')
    assert os.readlink(binding_dir / 'sh') == native.tool('sh')
    assert environment['SHELL'] == environment['CONFIG_SHELL'] == native.tool('sh')
    assert all(environment[name] == '' for name in ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'))
    assert environment['CC'] != native.tool('cc') and environment['CXX'] != native.tool('cxx')
    shell = subprocess.run(['sh', str(config_guess)], cwd=args.work, env=environment,
                           capture_output=True, text=True)
    assert shell.returncode == 0, (shell.returncode, shell.stdout, shell.stderr, environment['PATH'])
    expected_triple = shell.stdout.strip()
    assert expected_triple.startswith('arm64-apple-darwin'), expected_triple

    cmake_script = args.work / 'get-host-triple.cmake'
    llvm = args.source.resolve() / 'llvm'
    cmake_script.write_text(
        f'set(LLVM_MAIN_SRC_DIR "{llvm.as_posix()}")\n'
        f'include("{(llvm / "cmake/modules/GetHostTriple.cmake").as_posix()}")\n'
        'get_host_triple(HOST_TRIPLE)\n'
        'message(STATUS "selected host triple: ${HOST_TRIPLE}")\n', encoding='utf-8')
    failed = subprocess.run([native.tool('cmake'), '-P', str(cmake_script)],
        cwd=args.work, env=baseline, capture_output=True, text=True)
    assert failed.returncode != 0 and 'Failed to execute' in failed.stderr, failed.stderr
    passed = subprocess.run([native.tool('cmake'), '-P', str(cmake_script)],
        cwd=args.work, env=environment, capture_output=True, text=True)
    assert passed.returncode == 0, passed.stderr
    assert 'selected host triple: ' + expected_triple in passed.stdout, passed.stdout

    definition = targets.target_definition(args.target)
    compiler_plain = target_toolchain.clang_compiler(str(args.target_prefix.resolve()),
        definition['triplet'], host=dict(native.host), env=baseline)
    compiler_bound = target_toolchain.clang_compiler(str(args.target_prefix.resolve()),
        definition['triplet'], host=dict(native.host), env=environment)
    assert compiler_bound == compiler_plain, 'native shell binding changed the target compiler selection'
    producer = module(FILES / 'build.py', 'native_shell_builder')
    argv = producer.cmake_arguments(args.source.resolve(), args.work / 'build',
        args.work / 'stage', args.work / 'sysroot', native, compiler_bound,
        definition, '23.1.4', 'bootstrap')
    options = dict(item[2:].split('=', 1) for item in argv if item.startswith('-D'))
    assert options['CMAKE_C_COMPILER'] == compiler_bound['binaries']['cc']['selected_path']
    assert options['CMAKE_CXX_COMPILER'] == compiler_bound['binaries']['cxx']['selected_path']
    assert options['CMAKE_C_COMPILER'] != environment['CC']
    assert options['CMAKE_CXX_COMPILER'] != environment['CXX']
    for name in ('CMAKE_C_FLAGS', 'CMAKE_CXX_FLAGS', 'CMAKE_ASM_FLAGS'):
        flags = shlex.split(options[name])
        assert not any(word.startswith('/foreign/host/') for word in flags), (name, flags)
    for name in ('CMAKE_C_COMPILER_TARGET', 'CMAKE_CXX_COMPILER_TARGET', 'CMAKE_ASM_COMPILER_TARGET'):
        assert options[name] == definition['triplet'], (name, options[name])
    assert options['CMAKE_SYSROOT'] == str(args.work / 'sysroot')
    assert options['CMAKE_FIND_ROOT_PATH_MODE_INCLUDE'] == 'ONLY'
    assert options['CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH'] == 'OFF'
    target_source = args.work / 'target-probe.c'
    target_source.write_text('int runtime_target_probe(void) { return 0; }\n', encoding='utf-8')
    compile_argv = [options['CMAKE_C_COMPILER'], '--target=' + definition['triplet'],
        '--sysroot=' + options['CMAKE_SYSROOT'], *shlex.split(options['CMAKE_C_FLAGS']),
        '-fsyntax-only', str(target_source)]
    target_runs = [subprocess.run(compile_argv, cwd=args.work, env=env,
        capture_output=True, text=True) for env in (baseline, environment)]
    assert all(run.returncode == 0 for run in target_runs), [run.stderr for run in target_runs]
    assert target_runs[0].stderr == target_runs[1].stderr
    assert all('/foreign/host/' not in run.stderr for run in target_runs)
    print('PASS: literal sh/config.guess and CMake host-triple lookup use selected mksh; target Clang flags stay explicit')


if __name__ == '__main__':
    main()
