#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check real pkgsrc host-context provider metadata with shared PFFFT on and off."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p=argparse.ArgumentParser(description=__doc__)
for name in ('bmake','pkgsrc','makeconf'):
    p.add_argument('--'+name, type=Path, required=True)
a=p.parse_args()
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44'
with tempfile.TemporaryDirectory(prefix='electron-font-host-context-') as tmp:
    root=Path(tmp).resolve()
    for item in a.pkgsrc.resolve().iterdir():
        if item.name!='devel': (root/item.name).symlink_to(item)
    (root/'devel').mkdir()
    for item in (a.pkgsrc/'devel').iterdir():
        if item.name!='electron-host-context': (root/'devel'/item.name).symlink_to(item.resolve())
    package=root/'devel/electron-host-context'
    shutil.copytree(owner/'files/host-buildlink',package)
    def query(enabled):
        expression='${_BUILDLINK_TREE}|${BUILDLINK_API_DEPENDS.pffft}|${BUILDLINK_ABI_DEPENDS.pffft}'
        prefix=a.bmake.resolve().parent.parent
        cmd=[str(a.bmake),'-r','MAKECONF='+str(a.makeconf),'USE_CROSS_COMPILE=no',
             'LOCALBASE='+str(prefix),'PKG_DBDIR='+str(prefix/'pkgdb'),
             'PKGSRC_COMPILER=clang','CLANGBASE='+str(prefix),'CC='+str(prefix/'bin/clang'),
             'CXX='+str(prefix/'bin/clang++'),
             'EMBERBSD_ELECTRON_HOST_DEPENDENCIES='+str(owner/'host-dependencies.mk'),
             'EMBERBSD_ELECTRON_SHARED_PFFFT='+('yes' if enabled else 'no'),'-V',expression]
        result=subprocess.run(cmd,cwd=package,env={'PATH':os.environ['PATH'],'HOME':os.environ.get('HOME','/')},text=True,capture_output=True)
        assert result.returncode==0,result.stdout+result.stderr
        return result.stdout.strip().splitlines()[-1].split('|')
    off=query(False);on=query(True)
    assert 'pffft' in on[0].split(),on
    for value in on[1:]: assert 'pffft>=1.1.0nb2' in value.split(),on
    assert all('pffft>=1.1.0nb2' not in value.split() for value in off[1:]),off
print('PASS: host context selects PFFFT floor only when enabled')
