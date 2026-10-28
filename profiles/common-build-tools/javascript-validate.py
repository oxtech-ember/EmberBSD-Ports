#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Validate a source-only Node package before its common pkgsrc installation."""
import argparse
import json
import os
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--name', required=True)
p.add_argument('--version', required=True)
p.add_argument('--dependency', action='append', default=[])
a = p.parse_args()
name = r'(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*'
if not re.fullmatch(name, a.name) or not a.source.is_absolute():
    p.error('select an absolute source and a valid module name')
manifest = json.loads((a.source / 'package.json').read_text(encoding='utf-8'))
if manifest.get('name') != a.name or manifest.get('version') != a.version:
    p.error('package name or version differs from its recipe')
expected = set(a.dependency)
if len(expected) != len(a.dependency) or not all(re.fullmatch(name, n) for n in expected):
    p.error('invalid or repeated selected dependency')
actual = set()
for field in ('dependencies', 'optionalDependencies'):
    values = manifest.get(field, {})
    if not isinstance(values, dict):
        p.error('invalid runtime dependency metadata')
    actual.update(values)
peer = manifest.get('peerDependencies', {})
peer_meta = manifest.get('peerDependenciesMeta', {})
if not isinstance(peer, dict) or not isinstance(peer_meta, dict):
    p.error('invalid peer dependency metadata')
actual.update(name for name in peer if not peer_meta.get(name, {}).get('optional', False))
if actual != expected:
    p.error('runtime dependencies differ from the recipe')
for current, dirs, files in os.walk(a.source, followlinks=False):
    root = Path(current)
    if any(entry.casefold() == 'node_modules' for entry in dirs + files):
        p.error('nested node_modules must use common providers')
    if any((root / entry).is_symlink() for entry in dirs + files):
        p.error('source package contains a symlink')
print('validated common JS source', a.name, a.version)
