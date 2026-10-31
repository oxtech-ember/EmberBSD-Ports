#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that the CMake Find modules leave Homebrew, Fink and MacPorts alone.

FindPython and CMakeFindFrameworks searched /opt/homebrew/Frameworks and
/usr/local/Frameworks before the search path, so a cross build that had only
the Ports prefix on its search path used a Homebrew Python. FindRuby ran brew
and FindGTK2 listed the Fink, MacPorts and Homebrew library directories.
The test traces a native and a cross configure that load these modules. No
traced line of them may name a foreign prefix or call brew, and the cross
FindPython must take the Python on the search path.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
MODULES = ('/Modules/FindPython/Support.cmake', '/Modules/CMakeFindFrameworks.cmake',
           '/Modules/FindRuby.cmake', '/Modules/FindGTK2.cmake')
FOREIGN = ('/opt/homebrew', '/usr/local/Frameworks', '/sw/lib', '/opt/local/lib',
           '_RUBY_CHECK_BREW()')


def configure(cmake, ninja, source, build, environment, extra):
    result = subprocess.run([str(cmake), '-S', str(source), '-B', str(build), '-G', 'Ninja',
                             '-DCMAKE_MAKE_PROGRAM=' + str(ninja), '--trace-expand', *extra],
                            capture_output=True, text=True, env=environment)
    return result.returncode, result.stdout, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', type=Path, required=True, help='absolute Ports cmake executable')
    parser.add_argument('--ninja', type=Path, required=True, help='absolute ninja executable')
    parser.add_argument('--python', type=Path, required=True, help='absolute Ports python3 executable')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        print('SKIP: Darwin only')
        return 0
    failures = []
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        tools = work / 'bin'
        tools.mkdir()
        (tools / 'python3').symlink_to(args.python)
        environment = {'LC_ALL': 'C', 'PATH': str(tools), 'HOME': temporary}
        cases = {
            'native': ('find_package(Python3 COMPONENTS Interpreter)\n'
                       'include(CMakeFindFrameworks)\n'
                       'cmake_find_frameworks(EmberBSDNone)\n'
                       'find_package(Ruby QUIET)\n'
                       'find_package(GTK2 QUIET)\n', []),
            'cross': ('find_package(Python3 COMPONENTS Interpreter)\n'
                      'message(STATUS "EMBERBSD_PYTHON=${Python3_EXECUTABLE}")\n',
                      ['-DCMAKE_SYSTEM_NAME=NetBSD',
                       '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER']),
        }
        for name, (body, extra) in cases.items():
            source = work / name
            source.mkdir()
            (source / 'CMakeLists.txt').write_text(
                'cmake_minimum_required(VERSION 3.20)\nproject(foreign NONE)\n' + body)
            code, out, err = configure(args.cmake, args.ninja, source, work / (name + '-build'),
                                       environment, extra)
            if code != 0:
                errors = [l for l in (out + err).splitlines() if 'Error' in l or 'error' in l]
                failures.append(name + ' configure failed: ' + ' '.join(errors[:5]))
                continue
            for line in err.splitlines():
                if line.split('(')[0].endswith(MODULES):
                    failures += [name + ': ' + line.strip() for f in FOREIGN if f in line]
            if name == 'cross':
                wanted = {'-- EMBERBSD_PYTHON=' + str(p) for p in (tools / 'python3', args.python)}
                if not wanted.intersection(out.splitlines()):
                    found = [l for l in out.splitlines() if 'EMBERBSD_PYTHON=' in l]
                    failures.append('cross FindPython did not take the search path Python: '
                                    + ' '.join(found))
    if failures:
        print('FAIL: ' + '\n'.join(sorted(set(failures))))
        return 1
    print('PASS: Find modules search neither Homebrew, Fink nor MacPorts')
    return 0


if __name__ == '__main__':
    sys.exit(main())
