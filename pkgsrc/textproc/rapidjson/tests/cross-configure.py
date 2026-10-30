#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check that a cross build of rapidjson builds no unit tests or examples.

The unit tests and examples are target programs that the build host cannot
run, and the package installs neither. Building them in a cross build only
adds failures in test code (writertest.cpp with the target libc++), and the
tests also include CTest, whose host-information query runs the build
host's sw_vers and ps during configure. A cross configure must leave both
off and must not run those host probes; the headers, CMake and pkg-config
files are still configured.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', required=True,
                        help='Ports make command for a cross build: PKGPATH, then bmake arguments')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rapidjson-cross-') as temporary:
        work = Path(temporary).resolve()
        make = [args.make, 'textproc/rapidjson', 'WRKOBJDIR=' + str(work)]
        query = subprocess.run([*make, '-V', '${USE_CROSS_COMPILE}', '-V', '${WRKSRC}',
                                '-V', '${CONFIGURE_DIRS}', '-V', '${BUILD_DEPENDS:M*googletest*}'],
                               capture_output=True, text=True, check=True).stdout.splitlines()
        cross, wrksrc, configure_dir, googletest = (query + [''] * 4)[:4]
        if cross.lower() != 'yes':
            print('FAIL: --make must run a cross build (USE_CROSS_COMPILE=%r)' % cross)
            return 1
        proc = subprocess.run([*make, 'configure'], capture_output=True, text=True)
        output = proc.stdout + proc.stderr
        caches = sorted(Path(wrksrc).glob('**/CMakeCache.txt'))
        cache = caches[0].read_text(errors='replace') if caches else ''
        problems = []
        if proc.returncode:
            problems.append('configure status %d' % proc.returncode)
        for option in ('RAPIDJSON_BUILD_TESTS', 'RAPIDJSON_BUILD_EXAMPLES'):
            if option + ':BOOL=OFF' not in cache:
                problems.append(option + ' is not OFF')
        if googletest:
            problems.append('googletest is a build dependency: ' + googletest)
        for probe in ('sw_vers', 'ps: command not found'):
            if probe in output:
                problems.append('configure ran the host probe: ' + probe)
        if caches and (caches[0].parent / 'test').exists():
            problems.append('the test directory was configured')
        if problems:
            print('FAIL: ' + '; '.join(problems))
            print(output[-2000:])
            return 1
    print('PASS: cross rapidjson configures without unit tests, examples or host probes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
