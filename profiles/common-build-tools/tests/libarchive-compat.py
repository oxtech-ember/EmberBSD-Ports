#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run common libarchive security tests and compare tar header diagnostics.

Both tar binaries must be built from the same source and tools; the baseline
omits only the common tar behavior patch. The test programs use the patched
source tree, including its workspace-contained absolute-path security test.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bsdtar', 'baseline', 'libarchive-test', 'bsdtar-test', 'test-source', 'work-dir'):
    parser.add_argument('--' + name, required=True, type=Path)
parser.add_argument('--tool-path', required=True, help='colon-separated selected absolute tool directories')
args = parser.parse_args()
for name, value in vars(args).items():
    if name == 'tool_path':
        continue
    if not value.is_absolute() or not value.exists():
        parser.error('all selected paths must exist and be absolute')
if any(not Path(part).is_absolute() or not Path(part).is_dir()
       for part in args.tool_path.split(os.pathsep)):
    parser.error('--tool-path requires existing absolute directories')
with tempfile.TemporaryDirectory(prefix='libarchive-compat-', dir=args.work_dir) as tmp:
    work = Path(tmp)
    env = dict(os.environ, TMPDIR=tmp, PATH=args.tool_path, LC_ALL='C')
    subprocess.run([args.libarchive_test, '-r', args.test_source / 'libarchive/test',
                    'test_write_disk_secure', 'test_write_disk_secure_symlinks_only',
                    'test_write_disk_secure744', 'test_write_disk_secure745',
                    'test_write_disk_secure746a', 'test_write_disk_secure746b'],
                   cwd=work, env=env, check=True)
    subprocess.run([args.bsdtar_test, '-p', args.bsdtar, '-r', args.test_source / 'tar/test',
                    'test_option_safe_writes', 'test_option_U_upper', 'test_symlink_dir'],
                   cwd=work, env=env, check=True)
    first, second = 'a' * 125, 'b' * 140
    (work / first).mkdir()
    (work / first / second).write_text('x')
    def diagnostic(binary):
        run = subprocess.run([binary, '-cvf', work / 'output.tar', '--format', 'ustar',
                              first + '/' + second], cwd=work, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return run.stderr
    baseline, fixed = diagnostic(args.baseline), diagnostic(args.bsdtar)
    if ('Pathname too long' not in baseline or 'Pathname too long' not in fixed or
            fixed.count('a ') <= baseline.count('a ')):
        raise SystemExit('verbose header-error behavior did not change as expected')
print('Common libarchive security and tar behavior checks passed')
