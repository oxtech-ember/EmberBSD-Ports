#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Prove byte-identical Node configure provider path transitions."""
from collections import Counter
import hashlib
import os
from pathlib import Path
import stat
import subprocess


def _file(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError('GYP proof requires a canonical regular file: ' + str(path))
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('GYP proof input is not regular: ' + str(path))
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    after = path.stat()
    if any(getattr(before, x) != getattr(after, x) for x in
           ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
        raise ValueError('GYP proof input changed while reading: ' + str(path))
    return digest


def _inventory(root):
    base = root / 'devel/gyp'
    if not base.is_dir() or base.is_symlink() or base.resolve(strict=True) != base:
        raise ValueError('invalid GYP recipe directory')
    entries = {}
    def failed(error):
        raise error
    for parent, dirs, files in os.walk(base, followlinks=False, onerror=failed):
        for name in dirs + files:
            p = Path(parent) / name
            if p.is_symlink() or p.resolve(strict=True) != p:
                raise ValueError('GYP recipe entry is not canonical')
            rel = p.relative_to(root).as_posix()
            if p.is_dir():
                entries[rel] = None
            else:
                entries[rel] = _file(p)
    return entries


def verify(old, new, python, sdk_source, env, selected_node_owner):
    """Return only keys covered by verified GYP and declared helper transitions."""
    inputs_key = 'emberbsd_node_configure_inputs'
    deps_key = 'emberbsd_node_configure_dependencies'
    def parse(value):
        if type(value) is not list or any(type(row) is not str for row in value):
            raise ValueError('invalid Node configure inputs')
        pairs = [row.partition('=') for row in value]
        if any(not k or not sep or not v for k, sep, v in pairs) or len({k for k, _, _ in pairs}) != len(pairs):
            raise ValueError('invalid or duplicate Node configure input')
        return [(k, v) for k, _, v in pairs]
    before, after = parse(old.get(inputs_key)), parse(new.get(inputs_key))
    a, b = dict(before), dict(after)
    helper_key = 'emberbsd_node_configure_helper'
    old_helper, new_helper = old.get(helper_key), new.get(helper_key)
    if not isinstance(old_helper, str) or not isinstance(new_helper, str):
        raise ValueError('invalid Node configure helper')
    selected = Path(selected_node_owner)
    if (not selected.is_absolute() or selected.is_symlink() or
            selected.resolve(strict=True) != selected or not selected.is_dir()):
        raise ValueError('invalid selected Node owner')
    suffix = Path('scripts/source-inputs/node/configure-inputs.py')
    helpers = []
    for raw in (old_helper, new_helper):
        path = Path(raw)
        if not path.is_absolute() or str(path) != raw or '..' in path.parts or len(path.parents) < 4:
            raise ValueError('invalid Node configure helper path')
        owner = path.parents[3]
        if path != owner / suffix or not owner.is_dir() or owner.resolve(strict=True) != owner:
            raise ValueError('invalid declared Node configure helper')
        helpers.append(path)
    if helpers[1] != selected / suffix:
        raise ValueError('Node configure helper does not belong to selected owner')
    if _file(helpers[0]) != _file(helpers[1]):
        raise ValueError('Node configure helper bytes differ')
    gyp_changed = before != after
    helper_changed = old_helper != new_helper
    if not gyp_changed and not helper_changed:
        return set()
    if ([k for k, _ in before] != [k for k, _ in after] or
            any(a[k] != b[k] for k in a if k != 'gyp-pkgsrc')):
        raise ValueError('Node configure changed beyond GYP export root')
    roots = []
    for raw in (a['gyp-pkgsrc'], b['gyp-pkgsrc']):
        root = Path(raw)
        if not root.is_absolute() or str(root) != raw or root.is_symlink() or root.resolve(strict=True) != root or not root.is_dir():
            raise ValueError('invalid GYP export root')
        roots.append(root)
    if roots[0] != roots[1] and (roots[0].is_relative_to(roots[1]) or roots[1].is_relative_to(roots[0])):
        raise ValueError('invalid GYP export transition')
    inventory = _inventory(roots[0])
    if inventory != _inventory(roots[1]):
        raise ValueError('GYP recipe inventory differs')
    for rel in ('EMBERBSD-PKGSRC-REVISION', 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py'):
        if _file(roots[0] / rel) != _file(roots[1] / rel):
            raise ValueError('GYP export identity input differs: ' + rel)
    old_deps, new_deps = old.get(deps_key), new.get(deps_key)
    if any(type(v) is not list or any(type(x) is not str for x in v) for v in (old_deps, new_deps)):
        raise ValueError('invalid Node configure dependencies')
    if old_deps.count(old_helper) != 1 or new_deps.count(new_helper) != 1:
        raise ValueError('Node configure helper dependency must occur exactly once')
    source = Path(a['gyp-source'])
    if not source.is_absolute() or source.is_symlink() or source.resolve(strict=True) != source or not source.is_dir():
        raise ValueError('invalid prepared GYP source')
    if old_deps.count(str(source / 'emberbsd-prepared-source.json')) < 1:
        raise ValueError('missing prepared GYP receipt')
    _file(source / 'emberbsd-prepared-source.json')
    required = [rel for rel, value in inventory.items() if value is not None]
    required += ['EMBERBSD-PKGSRC-REVISION', 'EMBERBSD-SOURCE-IDENTITY/pkgsrc-source-identity.py']
    if any(str(roots[0] / rel) not in old_deps or str(roots[1] / rel) not in new_deps for rel in required):
        raise ValueError('missing GYP configure dependency')
    mapped, origins = [], {}
    for raw in old_deps:
        path = Path(raw)
        if not path.is_absolute() or str(path) != raw or '..' in path.parts:
            raise ValueError('invalid Node configure dependency path')
        if raw == old_helper:
            dest = new_helper
        elif path.is_relative_to(roots[0]):
            rel = path.relative_to(roots[0])
            newpath = roots[1] / rel
            if _file(path) != _file(newpath):
                raise ValueError('GYP moved dependency differs: ' + str(rel))
            dest = str(newpath)
        else:
            dest = raw
        if dest in origins and origins[dest] != raw:
            raise ValueError('GYP dependency mapping collision')
        origins[dest] = raw
        mapped.append(dest)
    if Counter(mapped) != Counter(new_deps):
        raise ValueError('Node configure dependencies differ')
    for root in dict.fromkeys(roots):
        verifier = root / 'devel/gyp/files/verify-source.py'
        subprocess.run([str(python), '-B', str(verifier), '--sdk-source', str(sdk_source),
                        '--source', a['gyp-source'], '--pkgsrc-root', str(root)], env=env, check=True)
    allowed = {deps_key}
    if gyp_changed:
        allowed.add(inputs_key)
    if helper_changed:
        allowed.add(helper_key)
    return allowed
