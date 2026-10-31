#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check errno_t declarations and library type information."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cppcheck', type=Path, required=True)
parser.add_argument('--std-cfg', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory(dir=args.work_dir) as tmp:
    root = Path(tmp)
    executable = root / 'cppcheck'
    shutil.copy2(args.cppcheck.resolve(strict=True), executable)
    (root / 'cfg').mkdir()
    shutil.copy2(args.std_cfg.resolve(strict=True), root / 'cfg' / 'std.cfg')
    for platform in ('unix32', 'unix64'):
        for label, declaration in (('typedef', 'typedef int errno_t;\n'), ('cfg-only', '')):
            source = root / (label + '.cpp')
            source.write_text(declaration + 'errno_t f(errno_t n) { return n / 0; }\n')
            result = subprocess.run([str(executable), '--std=c++17', '--platform=' + platform, str(source)],
                                    cwd=root, env=os.environ.copy(), text=True, capture_output=True)
            output = result.stdout + result.stderr
            if result.returncode or '[zerodiv]' not in output or '[syntaxError]' in output:
                raise SystemExit(f'{label} on {platform} failed or lost diagnostics:\n{output}')
print('PASS: errno_t declarations and configured type on unix32/unix64')
