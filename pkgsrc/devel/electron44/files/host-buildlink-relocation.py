#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Prove two owner-generated host buildlink views are equivalent."""
import hashlib
import os
import re
import stat
from pathlib import Path


def verify(old, new, old_work, new_work, owner):
    """Compare live records across two canonical exports without modifying either."""
    works = (Path(old_work), Path(new_work))
    records = (old, new)
    roots = []
    for record, work in zip(records, works):
        if not work.is_absolute() or work.is_symlink() or work.resolve(strict=True) != work:
            raise ValueError('invalid host buildlink work')
        invocation = record.get('invocation')
        identity = record.get('identity')
        if not isinstance(invocation, dict) or invocation.get('work') != str(work) or not isinstance(identity, dict) or set(identity) != {'inputs', 'links'}:
            raise ValueError('invalid host buildlink record')
        root = Path(invocation.get('pkgsrc_root', ''))
        if (not root.is_absolute() or root.is_symlink() or root.resolve(strict=True) != root or
                not (root / 'mk/bsd.pkg.mk').is_file()):
            raise ValueError('invalid host buildlink export root')
        if work.is_relative_to(root) or root.is_relative_to(work):
            raise ValueError('host buildlink work overlaps export root')
        roots.append(root)
    if roots[0] == roots[1] or roots[0].is_relative_to(roots[1]) or roots[1].is_relative_to(roots[0]):
        raise ValueError('invalid host buildlink export transition')
    before = {k:v for k,v in old['invocation'].items() if k not in ('work', 'pkgsrc_root')}
    after = {k:v for k,v in new['invocation'].items() if k not in ('work', 'pkgsrc_root')}
    if before != after:
        raise ValueError('host buildlink invocation changed')
    if old['identity']['links'] != new['identity']['links'] or not old['identity']['links']:
        raise ValueError('host buildlink links changed')

    mapped, directories = [], []
    for record, work, root in zip(records, works, roots):
        inputs, links = record['identity']['inputs'], record['identity']['links']
        if not isinstance(inputs, dict) or not isinstance(links, dict) or not inputs:
            raise ValueError('invalid host buildlink inputs')
        view = work / 'objects/devel/electron-host-context/work/.buildlink'
        if not view.is_dir() or view.is_symlink() or view.resolve(strict=True) != view:
            raise ValueError('invalid host buildlink view')
        actual_links, actual_directories = {}, set()
        def raise_walk_error(error):
            raise error
        for parent, dirs, files in os.walk(view, followlinks=False, onerror=raise_walk_error):
            for name in dirs + files:
                path = Path(parent) / name
                if path.is_symlink():
                    if path.resolve(strict=True).is_dir():
                        raise ValueError('host buildlink directory symlink is unsupported')
                    actual_links[str(path.relative_to(view))] = os.readlink(path)
                elif path.is_file():
                    if str(path.resolve(strict=True)) not in inputs:
                        raise ValueError('host buildlink generated file is not recorded')
                elif path.is_dir():
                    actual_directories.add(str(path.relative_to(view)))
                else:
                    raise ValueError('host buildlink view has a special file')
        directories.append(actual_directories)
        if actual_links != links:
            raise ValueError('live host buildlink links differ from record')
        for relative, target in links.items():
            if not isinstance(relative, str) or not isinstance(target, str):
                raise ValueError('invalid host buildlink link')
            rel = Path(relative); destination = Path(target)
            if (not rel.parts or rel.is_absolute() or str(rel) != relative or
                    any(part in ('.', '..') for part in rel.parts) or not destination.is_absolute()):
                raise ValueError('invalid host buildlink link path')
            link = view / rel
            if not link.is_symlink() or os.readlink(link) != target:
                raise ValueError('host buildlink link differs from record')
            resolved = link.resolve(strict=True)
            if not resolved.is_file() or str(resolved) not in inputs:
                raise ValueError('host buildlink target is not recorded')
        normalized = {}
        for name, recorded in inputs.items():
            if not isinstance(name, str) or not isinstance(recorded, str) or not re.fullmatch(r'[0-9a-f]{64}', recorded):
                raise ValueError('invalid host buildlink input record')
            path = Path(name)
            if (not path.is_absolute() or str(path) != name or '..' in path.parts or path.is_symlink() or
                    path.resolve(strict=True) != path):
                raise ValueError('invalid host buildlink input path')
            before_stat = path.stat()
            if not stat.S_ISREG(before_stat.st_mode):
                raise ValueError('host buildlink input is not regular')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != recorded:
                raise ValueError('host buildlink input differs from record: ' + name)
            if path.is_relative_to(work):
                key = ('work', path.relative_to(work).as_posix())
                value = owner._normal_work_file(path, work)
            elif path.is_relative_to(root):
                key = ('export', path.relative_to(root).as_posix())
                value = actual
            else:
                key = ('external', name)
                value = actual
            after_stat = path.stat()
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if any(getattr(before_stat, field) != getattr(after_stat, field) for field in fields):
                raise ValueError('host buildlink input changed during verification')
            if key in normalized:
                raise ValueError('colliding host buildlink input paths')
            normalized[key] = value
        mapped.append(normalized)
    if directories[0] != directories[1]:
        raise ValueError('host buildlink directory layout changed')
    if mapped[0].keys() != mapped[1].keys():
        raise ValueError('host buildlink input set changed')
    if not any(key[0] == 'work' for key in mapped[0]):
        raise ValueError('host buildlink generated inputs are missing')
    for key in mapped[0]:
        if mapped[0][key] != mapped[1][key] and not (key[0] == 'export' and key[1].startswith('mk/')):
            raise ValueError('host buildlink effective input changed: ' + '/'.join(key))
