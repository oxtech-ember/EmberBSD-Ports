#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check Clang importer handles unnamed macro parameters without losing diagnostics."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cppcheck', type=Path, required=True)
p.add_argument('--clang', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
a = p.parse_args()
with tempfile.TemporaryDirectory(dir=a.work_dir) as tmp:
    root = Path(tmp)
    (root / 'decl.h').write_text('#define DECLARE(name, type) void name(type)\n')
    source = root / 'check.c'
    source.write_text('#include "decl.h"\nDECLARE(example, int);\n'
                      'int check(int value) { return value / 0; }\n')
    result = subprocess.run([str(a.cppcheck.resolve(strict=True)),
                             '--clang=' + str(a.clang.resolve(strict=True)), str(source)],
                            cwd=root, env=os.environ.copy(), text=True, capture_output=True)
    if result.returncode or '[zerodiv]' not in result.stdout + result.stderr:
        raise SystemExit('Clang importer failed or lost diagnostics:\n' + result.stdout + result.stderr)
print('PASS: unnamed macro parameter and ordinary diagnostic')
