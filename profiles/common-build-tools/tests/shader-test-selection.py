#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate SPIRV-Tools and glslang production metadata with bmake."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--work-parent', type=Path, required=True)
args = parser.parse_args()
if not args.bmake.is_absolute() or not args.bmake.is_file():
    raise SystemExit('Select an absolute bmake executable')
if not args.work_parent.is_absolute() or not args.work_parent.is_dir():
    raise SystemExit('Select an existing absolute work parent')
repo = Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='shader-test-metadata-', dir=args.work_parent) as work:
    fixture = Path(work) / 'fixture.mk'
    for recipe in ('parallel/spirv-tools', 'graphics/glslang'):
        source = (repo / 'pkgsrc' / recipe / 'Makefile').read_text()
        lines = []
        for line in source.splitlines():
            if line.lstrip().startswith('.include '):
                line = 'TEST_INCLUDES+= ' + line.split('"')[1]
            lines.append(line)
        for tests in (False, True):
            fixture.write_text('OPSYS=Linux\nUSE_CROSS_COMPILE=no\nPKG_OPTIONS=' +
                               ('tests' if tests else '') + '\n' + '\n'.join(lines) +
                               '\nshow:\n\t@printf "%s\\n" ${CMAKE_CONFIGURE_ARGS:Q}\n'
                               '\t@printf "%s\\n" ${TEST_INCLUDES:Q}\n')
            result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(fixture), 'show'],
                                    capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(recipe + ': ' + result.stderr)
            values = result.stdout.splitlines()
            if len(values) != 2:
                raise SystemExit('Missing metadata for ' + recipe)
            flags, includes = map(str.split, values)
            gtest = '../../devel/googletest/buildlink3.mk'
            if (gtest in includes) != tests:
                raise SystemExit(recipe + ': GoogleTest does not follow tests option')
            if recipe == 'parallel/spirv-tools':
                flag = '-DSPIRV_SKIP_TESTS=' + ('OFF' if tests else 'ON')
                deps = {'../../devel/effcee/buildlink3.mk', '../../devel/re2/buildlink3.mk'}
                if flag not in flags or (deps <= set(includes)) != tests:
                    raise SystemExit(recipe + ': test selection/dependencies mismatch')
            else:
                flag = '-DGLSLANG_TESTS=' + ('ON' if tests else 'OFF')
                if flag not in flags:
                    raise SystemExit(recipe + ': test selection mismatch')
print('PASS: four shader package test selections; no build')
