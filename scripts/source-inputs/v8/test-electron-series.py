#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Compare common V8 ordered patches to the pinned Electron upstream series."""
import argparse
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--git',required=True);p.add_argument('--electron-source',required=True);a=p.parse_args()
repo=Path(a.electron_source).resolve(strict=True)
patchdir=Path(__file__).resolve().parents[3]/'pkgsrc/lang/v8/patches'
revision='9ee9e7718172287d068cee397097c2d79a137eec'
def show(path):
    return subprocess.run([a.git,'-C',str(repo),'show',revision+':'+path],check=True,stdout=subprocess.PIPE).stdout
names=[x for x in show('patches/v8/.patches').decode().splitlines() if x and not x.startswith('#')]
expected=[]
for index,name in enumerate(names,1):
    target='patch-000-electron-%02d-%s' % (index,name.removesuffix('.patch'))
    expected.append(target)
    data=show('patches/v8/'+name)
    lines=[]
    for line in data.splitlines(keepends=True):
        if line.startswith(b'--- a/'): line=b'--- '+line[6:]
        if line.startswith(b'+++ b/'): line=b'+++ '+line[6:]
        lines.append(line)
    if (patchdir/target).read_bytes()!=b''.join(lines):
        raise SystemExit('Electron V8 patch mismatch: '+name)
if sorted(x.name for x in patchdir.glob('patch-000-electron-*'))!=sorted(expected):
    raise SystemExit('Electron V8 series inventory mismatch')
print('PASS:',len(expected),'ordered Electron V8 patches match verified Git object')
