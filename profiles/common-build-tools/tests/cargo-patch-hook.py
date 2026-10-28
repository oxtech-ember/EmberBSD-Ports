#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Run the common patch include at pre-configure on a real crate fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

p=argparse.ArgumentParser()
for name in ('prefix','bmake','archive'):
    p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); prefix=a.prefix.resolve(strict=True)
source=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='cargo-patch-hook-') as temp:
    root=Path(temp); sdk=root/'lang/rust';sdk.mkdir(parents=True)
    shutil.copyfile(source/'cargo-patches.mk',sdk/'emberbsd-cargo-patches.mk')
    shutil.copyfile(source/'cargo-patches.py',sdk/'emberbsd-cargo-patches.py')
    shutil.copytree(source/'cargo-patches',sdk/'emberbsd-cargo-patches')
    vendor=root/'vendor';vendor.mkdir();name='tracing-attributes-0.1.31'
    with tarfile.open(a.archive) as archive:archive.extractall(vendor,filter='data')
    checksum=hashlib.sha256(a.archive.read_bytes()).hexdigest()
    (vendor/name/'.cargo-checksum.json').write_text(json.dumps({'package':checksum,'files':{}}))
    makefile=root/'Makefile';makefile.write_text('.include "'+str(sdk/'emberbsd-cargo-patches.mk')+'"\n')
    args=[str(a.bmake),'-f',str(makefile),'EMBER_CARGO_PATCH_SET=yes','EMBER_CARGO_PREFIX='+str(prefix),
          'CARGO_VENDOR_DIR='+str(vendor),'TOOL_PYTHONBIN='+str(prefix/'bin/python3.15'),'pre-configure']
    for _ in range(2):subprocess.run(args,check=True,capture_output=True,text=True)
    manifest=(vendor/name/'Cargo.toml').read_text()
    assert '[dependencies.syn]\nversion = "3.0"' in manifest
    assert json.loads((vendor/name/'.cargo-checksum.json').read_text())['package']==checksum
print('common pre-configure hook, exact crate patch and repetition: PASS')
