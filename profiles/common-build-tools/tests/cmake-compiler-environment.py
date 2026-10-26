#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that CMake consumes selected pkgsrc compiler commands from its environment."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[3]


def cache(path, name):
    for line in path.read_text().splitlines():
        if line.startswith(name + ':'):
            return line.split('=', 1)[1]
    raise AssertionError('missing CMake cache entry: ' + name)


def configure(cmake, source, build, environment, extra=()):
    return subprocess.run([str(cmake), '-S', str(source), '-B', str(build),
        '-G', 'Unix Makefiles', *extra], env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--makeconf', type=Path, required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    environment = os.environ.copy()
    cc, cxx = shlex.split(environment.get('CC', '')), shlex.split(environment.get('CXX', ''))
    if not cc or not cxx or len(cc) < 2 or len(cxx) < 2:
        raise SystemExit('CC and CXX must each contain a selected compiler and ABI arguments')

    with tempfile.TemporaryDirectory(prefix='cmake-compiler-environment-', dir=args.work) as temporary:
        work = Path(temporary)
        source = work / 'source'
        source.mkdir()
        (source / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.20)\nproject(compiler_environment LANGUAGES C CXX)\n')

        # CMake must reject the old recipe form: a command with ABI words is not
        # itself an executable path. The environment path below must parse it.
        bad_args = ['-DCMAKE_C_COMPILER=' + ' '.join(cc),
                    '-DCMAKE_CXX_COMPILER=' + ' '.join(cxx)]
        broken = configure(args.cmake, source, work / 'broken', environment, bad_args)
        if broken.returncode == 0 or 'not a full path' not in broken.stdout:
            raise AssertionError('the malformed recipe compiler override did not reproduce CMake rejection:\n' +
                                 broken.stdout[-2000:])

        for package in ('devel/lld', 'lang/clang'):
            query = subprocess.run([str(args.bmake), '-C', str(args.pkgsrc / package),
                'MAKECONF=' + str(args.makeconf), 'show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS'],
                env=environment, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)
            if query.returncode:
                raise AssertionError(f'bmake could not render {package} CMAKE_CONFIGURE_ARGS:\n' +
                                     query.stdout[-3000:])
            configure_args = shlex.split(query.stdout.strip())
            build = work / package.replace('/', '-')
            result = configure(args.cmake, source, build, environment, configure_args)
            if result.returncode:
                raise AssertionError(f'CMake rejected {package} CMAKE_CONFIGURE_ARGS with selected CC/CXX:\n' +
                                     result.stdout[-4000:])
            cache_file = build / 'CMakeCache.txt'
            for language, command in (('C', cc), ('CXX', cxx)):
                selected = shutil.which(command[0], path=environment.get('PATH')) or command[0]
                actual = cache(cache_file, 'CMAKE_' + language + '_COMPILER')
                arguments = shlex.split(cache(cache_file, 'CMAKE_' + language + '_COMPILER_ARG1'))
                if os.path.realpath(actual) != os.path.realpath(selected) or arguments != command[1:]:
                    raise AssertionError(f'{package}: CMake did not preserve selected {language} compiler/ABI argv: '
                        f'compiler={actual!r}, arg1={arguments!r}, expected={command!r}')
    print('PASS: rendered LLD and Clang recipe arguments preserve the selected CC/CXX environment')
    print('PASS: CMake separates selected compiler executables from ABI argument words')
    print('PASS: the prior CMAKE_*_COMPILER command-string form is rejected')


if __name__ == '__main__':
    main()
