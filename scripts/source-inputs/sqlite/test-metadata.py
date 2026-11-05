#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SQLite full-source owner metadata and reject mismatched family versions."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
p=argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source','pkgsrc','archive'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); sys.path.insert(0,str(a.sdk_source.resolve(strict=True)/'src'))
from emberbsd_sdk import archive_metadata
source=Path(__file__).with_name('source.py'); spec=importlib.util.spec_from_file_location('sqlite_source',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m); owner=m.Owner(); owner.archive_metadata=archive_metadata
owner.read=lambda path:Path(path).read_bytes()
def require(condition,message):
    if not condition: raise ValueError(message)
owner.require=require
metadata,patches=owner.recipe(a.pkgsrc.resolve(strict=True))
data=a.archive.resolve(strict=True).read_bytes()
assert metadata['archive']=='sqlite-src-3540100.zip' and metadata['archive_root']=='sqlite-src-3540100'
assert metadata['size']==len(data) and metadata['sha512']==hashlib.sha512(data).hexdigest()
assert metadata['blake2s']==hashlib.blake2s(data).hexdigest() and len(patches)==1
with tempfile.TemporaryDirectory(prefix='sqlite-metadata-') as tmp:
    target=Path(tmp)/'databases/sqlite3'; shutil.copytree(a.pkgsrc/'databases/sqlite3',target)
    common=target/'Makefile.common'; common.write_text(common.read_text().replace('SQLITE3_VERSION=\t3.54.1','SQLITE3_VERSION=\t3.54.2'))
    try: owner.recipe(Path(tmp))
    except ValueError as error: assert 'versions differ' in str(error)
    else: raise AssertionError('mismatched family version accepted')
print('PASS: canonical SQLite fullsrc archive, patch inventory and family-version binding')
