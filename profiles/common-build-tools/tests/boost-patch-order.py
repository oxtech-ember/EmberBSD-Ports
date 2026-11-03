#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Verify the selected Boost export patch chain.
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[3]
upstream = root / 'upstream/pkgsrc'
patch = os.environ['PATCH']
files = {'devel/boost-headers/Makefile', 'devel/boost-headers/PLIST',
         'devel/boost-headers/buildlink3.mk', 'devel/boost-libs/Makefile',
         'devel/boost-libs/PLIST'}
target = 'profiles/common-build-tools/patches/pkgsrc-boost-headers-cmake-config.patch'
with tempfile.TemporaryDirectory(prefix='boost-patch-order-') as tmp:
    tree = Path(tmp)
    for name in files:
        dst = tree / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(upstream / name, dst)
    found = False
    for line in (root / 'pkgsrc/export.conf').read_text().splitlines():
        fields = line.split()
        if not fields or fields[0] != 'patch':
            continue
        rel = fields[1]
        content = (root / rel).read_text()
        parts = re.split(r'(?=^--- a/)', content, flags=re.MULTILINE)
        selected = [x for x in parts if x.startswith('--- a/') and x.splitlines()[0][6:] in files]
        if selected:
            subprocess.run([patch, '--forward', '-F0', '-p1', '-d', str(tree)],
                           input=''.join(selected), text=True, check=True)
        if rel == target:
            found = True
            break
    if not found:
        raise SystemExit('Boost export patch missing')
print('PASS: selected Boost patches apply in export order without fuzz')
