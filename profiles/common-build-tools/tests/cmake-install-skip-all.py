#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify pkgsrc CMake installs do not rebuild the completed ALL target."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True)
    parser.add_argument('--ninja', type=Path, required=True)
    parser.add_argument('--cc', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--pkgsrc-patch', type=Path, required=True)
    args = parser.parse_args()
    cmake = args.cmake.resolve(strict=True)
    ninja = args.ninja.resolve(strict=True)
    cc = args.cc.resolve(strict=True)
    work = args.work.resolve(strict=True)
    patch = args.pkgsrc_patch.resolve(strict=True).read_text()
    option = '-DCMAKE_SKIP_INSTALL_ALL_DEPENDENCY:BOOL=TRUE'
    if option not in patch:
        raise SystemExit('pkgsrc CMake integration does not skip install/strip -> all')

    with tempfile.TemporaryDirectory(prefix='cmake-install-skip-all-', dir=work) as tmp:
        root = Path(tmp)

        def run(command, environment=None):
            result = subprocess.run(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    env=environment)
            if result.returncode:
                raise SystemExit(f'command failed ({result.returncode}): {command[0]}\n'
                                 + result.stdout[-3000:])

        def configure(label, option_value):
            source = root / (label + '-source')
            build = root / (label + '-build')
            source.mkdir()
            counter = root / (label + '-all-count')
            payload = source / 'payload.txt'
            payload.write_text('install-only\n')
            (source / 'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.24)
project(install_skip_all C)
add_custom_target(always ALL
  COMMAND "${{CMAKE_COMMAND}}" -E echo build >> "{counter}")
install(FILES "{payload}" DESTINATION share/install-skip-all)
''')
            command = [str(cmake), '-S', str(source), '-B', str(build), '-G', 'Ninja',
                       '-DCMAKE_MAKE_PROGRAM=' + str(ninja),
                       '-DCMAKE_C_COMPILER=' + str(cc)]
            if option_value is not None:
                command.append('-DCMAKE_SKIP_INSTALL_ALL_DEPENDENCY:BOOL=' + option_value)
            run(command)
            return build, counter

        build, counter = configure('enabled', 'TRUE')
        run([str(ninja), '-C', str(build)])
        if counter.read_text().splitlines() != ['build']:
            raise SystemExit('initial explicit ALL build did not execute once')
        install_env = os.environ.copy()
        install_env['DESTDIR'] = str(build / 'stage')
        for _ in range(2):
            run([str(ninja), '-C', str(build), 'install/strip'], install_env)
        if counter.read_text().splitlines() != ['build']:
            raise SystemExit('repeated install/strip rebuilt ALL after pkgsrc build completed')
        installed = build / 'stage/usr/local/share/install-skip-all/payload.txt'
        if not installed.is_file() or installed.read_text() != 'install-only\n':
            raise SystemExit('install/strip did not install its payload')
        run([str(ninja), '-C', str(build), 'all'])
        if counter.read_text().splitlines() != ['build', 'build']:
            raise SystemExit('explicit ALL build no longer executes')

        for label, option_value in (('default', None), ('disabled', 'FALSE')):
            baseline, baseline_counter = configure(label, option_value)
            run([str(ninja), '-C', str(baseline)])
            baseline_env = os.environ.copy()
            baseline_env['DESTDIR'] = str(baseline / 'stage')
            run([str(ninja), '-C', str(baseline), 'install/strip'], baseline_env)
            if baseline_counter.read_text().splitlines() != ['build', 'build']:
                raise SystemExit(f'{label} control did not rebuild ALL before install/strip')

    print('PASS: install/strip installs without repeating ALL; explicit ALL still works')


if __name__ == '__main__':
    main()
