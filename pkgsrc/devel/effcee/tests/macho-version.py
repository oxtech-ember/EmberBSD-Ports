#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the recipe's Mach-O version calculation using CMake."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--cmake', required=True)
a = p.parse_args()
patch = (Path(__file__).resolve().parents[1] / 'patches/patch-installed-dependencies').read_text()
lines = patch.splitlines()
start = lines.index('+if(APPLE)')
end = lines.index('+endif()', start)
fragment = '\n'.join(line[1:] for line in lines[start:end + 1])
with tempfile.TemporaryDirectory(prefix='effcee-macho-') as directory:
    root = Path(directory)
    source = root / 'source'
    source.mkdir()
    (source / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.22.1)\n'
        'project(check LANGUAGES NONE)\nset(APPLE TRUE)\nset(PROJECT_VERSION_MAJOR 1)\n'
        'set(PROJECT_VERSION_MINOR ${TEST_YEAR})\nset(PROJECT_VERSION_PATCH ${TEST_PATCH})\n'
        'add_library(effcee INTERFACE)\n'
        + fragment + '\nget_target_property(v effcee MACHO_CURRENT_VERSION)\n'
        'file(WRITE "${CMAKE_BINARY_DIR}/version" "${v}")\n')
    for year, patchlevel, expected in ((2000, 0, '1.0.0'), (2026, 0, '1.26.0'),
                                      (2027, 2, '1.27.2'), (2255, 255, '1.255.255'),
                                      (1999, 0, None), (2256, 0, None), (2026, 256, None)):
        build = root / (str(year) + '-' + str(patchlevel))
        result = subprocess.run([a.cmake, '-S', str(source), '-B', str(build),
            '-DTEST_YEAR=' + str(year), '-DTEST_PATCH=' + str(patchlevel)], capture_output=True, text=True)
        if expected is None:
            if result.returncode == 0 or 'cannot be represented' not in result.stdout + result.stderr:
                raise SystemExit('Expected range rejection: ' + str(year))
        elif result.returncode or (build / 'version').read_text() != expected:
            raise SystemExit('Unexpected result for ' + str(year) + ': ' + result.stdout + result.stderr)
print('PASS: actual Mach-O version fragment, ordering and range')
