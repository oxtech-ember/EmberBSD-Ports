#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Prepare the common libiio recipe from verified local archives."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile

recipe = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/libiio'
archives, output = map(Path, sys.argv[1:3])
if not output.is_absolute() or output.exists() or output.is_symlink():
    raise SystemExit('Use a new absolute source directory')
patch = Path(os.environ['PATCH'])
if not patch.is_absolute() or not os.access(patch, os.X_OK):
    raise SystemExit('Select an absolute PATCH executable')
entries = [line.split() for line in (recipe/'files/sources.tsv').read_text().splitlines()]
for name, expected, url in entries:
    if hashlib.sha256((archives/name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Source checksum mismatch: '+name)
# Check the ordinary recipe patch checksums before creating output.
info = (recipe/'distinfo').read_text()
patches = sorted((recipe/'patches').glob('patch-*'))
for item in patches:
    # pkgsrc excludes its expanding identification line from patch checksums.
    payload=b''.join(line for line in item.read_bytes().splitlines(keepends=True) if b'$NetBSD' not in line)
    if f'SHA1 ({item.name}) = {hashlib.sha1(payload).hexdigest()}' not in info:
        raise SystemExit('Patch checksum mismatch: '+item.name)
output.mkdir(parents=True)
with tarfile.open(archives/entries[0][0]) as archive:
    prefix = archive.getmembers()[0].name.split('/')[0]+'/'
    for entry in archive.getmembers():
        if not entry.name.startswith(prefix): continue
        entry.name = entry.name[len(prefix):]
        if entry.name: archive.extract(entry, output, filter='data')
for item in patches:
    with item.open('rb') as stream:
        subprocess.run([str(patch),'-d',str(output),'-p0','--batch'],stdin=stream,check=True)
(output/'.ember').mkdir()
(output/'.ember/iio.h').write_bytes((archives/entries[1][0]).read_bytes())
(output/'.ember/sources.tsv').write_bytes((recipe/'files/sources.tsv').read_bytes())
(output/'.ember/distinfo').write_bytes((recipe/'distinfo').read_bytes())
print('Prepared common libiio source: '+str(output))
