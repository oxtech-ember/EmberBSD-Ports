#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test the upstream copyright scan's pkgsrc build-directory boundary."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile

RECIPE = Path(__file__).resolve().parents[1]
UPSTREAM_CHECKER = 'SPIRV-Tools-2026.4/utils/check_copyright.py'
NOTICE = '''/*
 * Copyright (c) 2016 The Khronos Group Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and/or associated documentation files (the
 * "Materials"), to deal in the Materials without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Materials, and to permit
 * persons to whom the Materials are furnished to do so, subject to the
 * following conditions: The above copyright notice and this permission notice
 * shall be included in all copies or substantial portions of the Materials.
 *
 * THE MATERIALS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER
 * DEALINGS IN THE MATERIALS.
 */
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_inputs(archive, patch):
    data = archive.read_bytes()
    distinfo = (RECIPE / 'distinfo').read_text()
    for label, algorithm in (('BLAKE2s', 'blake2s'), ('SHA512', 'sha512')):
        match = re.search(
            r'^' + label + r' \(SPIRV-Tools-2026\.4\.tar\.gz\) = ([0-9a-f]+)$',
            distinfo, re.M)
        require(match and hashlib.new(algorithm, data).hexdigest() == match[1],
                'SPIRV-Tools archive hash mismatch')
    size = re.search(r'^Size \(SPIRV-Tools-2026\.4\.tar\.gz\) = (\d+) bytes$',
                     distinfo, re.M)
    require(size and len(data) == int(size[1]), 'SPIRV-Tools archive size mismatch')
    patchsum = re.search(r'^SHA1 \(' + re.escape(patch.name) +
                         r'\) = ([0-9a-f]{40})$', distinfo, re.M)
    require(patchsum, 'patch checksum missing from distinfo')
    patch_sha1 = runpy.run_path(
        str(RECIPE.parents[2] / 'scripts/prepare-pkgsrc.py'))['patch_sha1']
    require(patch_sha1(patch) == patchsum[1], 'patch checksum mismatch')


def write_files(root, files):
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)


def run_checker(checker, root, name, expected_status, expected_output=(),
                absent_output=()):
    result = subprocess.run([sys.executable, str(checker)], cwd=root,
                            capture_output=True, text=True)
    output = result.stdout + result.stderr
    require(result.returncode == expected_status,
            name + ': unexpected exit ' + str(result.returncode) + ': ' + output)
    if expected_status == 0:
        require(not output.strip(), name + ': unexpected output: ' + output)
    for expected in expected_output:
        require(expected in output, name + ': missing expected finding: ' + output)
    for unexpected in absent_output:
        require(unexpected not in output, name + ': unexpected finding: ' + output)
    print('PASS: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    parser.add_argument('--patch-tool', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    for path in vars(args).values():
        require(path.is_absolute(), 'Use absolute input paths')
    require(args.patch_tool.is_file() and os.access(args.patch_tool, os.X_OK),
            'patch tool must be an executable file')
    require(args.work_parent.is_dir(), 'work parent must exist')
    verify_inputs(args.archive, args.patch)
    print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True),
          end='')
    work = Path(tempfile.mkdtemp(prefix='spirv-copyright-check-',
                                 dir=args.work_parent))
    try:
        with tarfile.open(args.archive, 'r:gz') as archive:
            member = archive.getmember(UPSTREAM_CHECKER)
            require(member.isfile(), 'upstream checker is not a regular file')
            original = archive.extractfile(member).read()
        baseline = work / 'upstream-check_copyright.py'
        baseline.write_bytes(original)
        patched_tree = work / 'patched'
        utils = patched_tree / 'utils'
        utils.mkdir(parents=True)
        patched = utils / 'check_copyright.py'
        patched.write_bytes(original)
        result = subprocess.run(
            [str(args.patch_tool), '-F', '0', '-p0', '-i', str(args.patch)],
            cwd=patched_tree, capture_output=True, text=True)
        output = result.stdout + result.stderr
        require(result.returncode == 0 and
                not re.search(r'fuzz|offset', output, re.I),
                'patch did not apply exactly: ' + output)

        generated = {
            'cmake-pkgsrc-build/DebugInfo.h': NOTICE,
            'cmake-pkgsrc-build/OpenCLDebugInfo100.h': NOTICE,
        }
        baseline_case = work / 'upstream-generated'
        write_files(baseline_case, generated)
        run_checker(baseline, baseline_case, 'upstream reports generated headers', 1,
                    ('./cmake-pkgsrc-build/DebugInfo.h has no Apache 2 license notice',
                     './cmake-pkgsrc-build/OpenCLDebugInfo100.h has no Apache 2 license notice'))

        generated_case = work / 'patched-generated'
        write_files(generated_case, generated)
        run_checker(patched, generated_case, 'patched checker skips pkgsrc generated headers', 0)

        source_case = work / 'source-control'
        write_files(source_case, generated | {
            'source/real_source.cpp':
                '/* Copyright (c) 2025 The Khronos Group Inc. */\nint source;\n'
        })
        run_checker(patched, source_case, 'real source without Apache remains rejected', 1,
                    ('./source/real_source.cpp has no Apache 2 license notice',),
                    ('./cmake-pkgsrc-build/',))

        similar_case = work / 'similarly-named-source-control'
        write_files(similar_case, generated | {
            'cmake-pkgsrc-build-extra/OpenCLDebugInfo100.h': NOTICE
        })
        run_checker(patched, similar_case,
                    'similarly named non-build directory remains checked', 1,
                    ('./cmake-pkgsrc-build-extra/OpenCLDebugInfo100.h has no Apache 2 license notice',),
                    ('./cmake-pkgsrc-build/DebugInfo.h',))
        print('PASS: four source-only copyright scope cases')
    finally:
        shutil.rmtree(work)
        require(not work.exists(), 'Owned copyright fixture remains')
        print('Removed owned fixture: ' + str(work))
        print(subprocess.check_output(['df', '-k', str(args.work_parent)], text=True),
              end='')


if __name__ == '__main__':
    main()
