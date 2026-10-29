#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Install a verified common AutoGen tearoff into NTP's build integration."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'pkgsrc', 'source', 'ntp'):
    parser.add_argument('--' + name, required=True)
a = parser.parse_args()
if not all(os.path.isabs(x) for x in (a.sdk_source, a.pkgsrc, a.source, a.ntp)):
    raise SystemExit('libopts integration: all paths must be absolute')
sys.path.insert(0, str(Path(a.sdk_source) / 'src'))
from emberbsd_sdk import jsonio, sourceprep

root = Path(a.source).resolve(strict=True)
record = jsonio.read_json(str(root / sourceprep.PREPARED_TREE_RECEIPT))
identity = record.get('identity') if isinstance(record, dict) else None
sourceprep.validate_prepared_tree(str(root), package='devel/autogen', identity=identity)
recipe = Path(a.pkgsrc).resolve(strict=True) / 'devel/autogen'
expected = {'devel/autogen/distinfo': hashlib.sha256((recipe / 'distinfo').read_bytes()).hexdigest()}
for path in sorted((recipe / 'patches').glob('patch-*')):
    expected['devel/autogen/patches/' + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
module_path = recipe / 'files/ember-libopts-recipe.py'
spec = importlib.util.spec_from_file_location('ember_libopts_recipe', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if (not isinstance(identity, dict) or identity.get('recipe') != expected or
        identity.get('generation_recipe') != module.generation_recipe(recipe)):
    raise SystemExit('libopts integration: prepared source differs from common AutoGen recipe')
ntp = Path(a.ntp).resolve(strict=True)
target = ntp / 'sntp/libopts'
if not target.is_dir() or target.is_symlink() or root == target or root in target.parents or target in root.parents:
    raise SystemExit('libopts integration: invalid source or NTP work directory')
# NTP owns only its Automake integration; all library data and licenses come
# from the single prepared AutoGen source.
integration = {name: (target / name).read_bytes() for name in ('Makefile.am', 'Makefile.in')}
shutil.rmtree(target)
shutil.copytree(root, target, symlinks=False, ignore=shutil.ignore_patterns(sourceprep.PREPARED_TREE_RECEIPT))
for name, data in integration.items():
    (target / name).write_bytes(data)
# Preserve shipped configure outputs rather than regenerating with host tools.
top_reference = (ntp / 'aclocal.m4').stat()
os.utime(ntp / 'configure.ac', ns=(top_reference.st_atime_ns, top_reference.st_mtime_ns))
reference = (ntp / 'sntp/aclocal.m4').stat()
stamp = min(reference.st_mtime_ns, (ntp / 'aclocal.m4').stat().st_mtime_ns)
os.utime(ntp / 'sntp/m4/ntp_libevent.m4', ns=(stamp, stamp))
for name in ('Makefile.am', 'm4/libopts.m4', 'm4/stdnoreturn.m4'):
    path = target / name
    if path.exists():
        os.utime(path, ns=(reference.st_atime_ns, reference.st_mtime_ns))
