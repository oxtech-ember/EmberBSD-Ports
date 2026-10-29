#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check target C++ dependencies are not selected for native cross-libtool."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bmake', required=True)
args = parser.parse_args()
policy = Path(__file__).resolve().parents[1] / 'cross/compiler-policy.mk'
with tempfile.TemporaryDirectory(prefix='cross-libtool-policy-') as tmp:
    root = Path(tmp)
    shutil.copyfile(policy, root / 'compiler-policy.mk')
    (root / 'fortran.mk').write_text('# no Fortran in this fixture\n')
    runtime = root / 'lang/compiler-rt/application-runtime.mk'
    runtime.parent.mkdir(parents=True)
    runtime.write_text('RUNTIME_SELECTED=yes\n')
    makefile = root / 'Makefile'
    makefile.write_text('PKGSRCDIR=' + str(root) + '\n.include "compiler-policy.mk"\n')
    def selected(cross, tools, languages):
        result = subprocess.run([args.bmake, '-r', '-f', str(makefile),
            'PKGPATH=devel/example', 'USE_CROSS_COMPILE=' + cross,
            'TOOLS_USE_CROSS_COMPILE=' + tools, 'USE_LANGUAGES=' + languages,
            'EMBERBSD_CROSS_COMPILER_FAMILY=clang', '-V', '${RUNTIME_SELECTED:Uno}'],
            cwd=root, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    assert selected('no', 'yes', 'c c++') == 'no'
    assert selected('yes', 'yes', 'c c++') == 'yes'
    assert selected('yes', 'yes', 'c') == 'no'
print('cross-libtool native and target C++ dependency selection: PASS')
