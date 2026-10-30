#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Apply exact-version shared crate patches to a prepared Cargo vendor tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_path(root, relative):
    p = Path(relative)
    if p.is_absolute() or not p.parts or any(x in ('..', '.') for x in p.parts):
        raise ValueError('unsafe patch path: ' + relative)
    target = root / p
    for item in (target, *target.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError('symlink in patched path: ' + str(item))
    if target.exists() and not target.is_file():
        raise ValueError('not a regular patch file: ' + str(target))
    return target


def checked_file(root, relative):
    target = checked_path(root, relative)
    if not target.is_file():
        raise ValueError('missing patch file: ' + str(target))
    return target


def apply(vendor, registry_dir, patch_tool, prefix):
    vendor = vendor.resolve(strict=True)
    registry_dir = registry_dir.resolve(strict=True)
    prefix = prefix.resolve(strict=True)
    patch_tool = patch_tool.resolve(strict=True)
    if not patch_tool.is_relative_to(prefix) or not patch_tool.is_file():
        raise ValueError('patch tool must resolve inside selected host prefix')
    registry = json.loads((registry_dir / 'registry.json').read_text())
    for name, spec in sorted(registry.items()):
        if not re.fullmatch(r'[a-zA-Z0-9_-]+-[0-9]+\.[0-9]+\.[0-9]+', name):
            raise ValueError('invalid exact crate identifier: ' + name)
        root = vendor / name
        if root.is_symlink():
            raise ValueError('invalid crate directory: ' + str(root))
        if not root.exists():
            continue
        if not root.is_dir():
            raise ValueError('invalid crate directory: ' + str(root))
        manifest = tomllib.loads(checked_file(root, 'Cargo.toml').read_text())['package']
        if name != manifest['name'] + '-' + manifest['version']:
            raise ValueError('crate identity mismatch: ' + name)
        patch = checked_file(registry_dir, spec['patch'])
        files = spec['files']
        if not files:
            raise ValueError('empty patch: ' + name)
        lines = patch.read_text().splitlines()
        headers = []
        for index, line in enumerate(lines):
            if not line.startswith('--- '):
                continue
            if index + 1 >= len(lines) or not lines[index + 1].startswith('+++ '):
                raise ValueError('malformed patch header: ' + name)
            old, new = line[4:], lines[index + 1][4:]
            if old == '/dev/null' and new.startswith('b/'):
                relative, operation = new[2:], 'create'
            elif new == '/dev/null' and old.startswith('a/'):
                relative, operation = old[2:], 'delete'
            elif old.startswith('a/') and new == 'b/' + old[2:]:
                relative, operation = old[2:], 'modify'
            else:
                raise ValueError('unsafe patch header: ' + name)
            checked_path(root, relative)
            expected = files.get(relative)
            if not isinstance(expected, dict) or set(expected) != {'before', 'after'}:
                raise ValueError('invalid patch file metadata: ' + name + '/' + relative)
            before, after = expected['before'], expected['after']
            for value in (before, after):
                if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)):
                    raise ValueError('invalid patch file hash: ' + name + '/' + relative)
            if (operation == 'create') != (before is None) or (operation == 'delete') != (after is None) or before == after:
                raise ValueError('patch operation differs from metadata: ' + name + '/' + relative)
            headers.append(relative)
        if len(headers) != len(set(headers)) or set(headers) != set(files):
            raise ValueError('patch files differ from registry: ' + name)
        state = set()
        for relative, expected in files.items():
            path = checked_path(root, relative)
            current = digest(path) if path.is_file() else None
            if current == expected['before']:
                state.add('before')
            elif current == expected['after']:
                state.add('after')
            else:
                raise ValueError('unrecognized source bytes: ' + name + '/' + relative)
        if len(state) != 1:
            raise ValueError('partially applied crate patch: ' + name)
        checksum_path = checked_file(root, '.cargo-checksum.json')
        checksum = json.loads(checksum_path.read_text())
        if not isinstance(checksum.get('files'), dict) or 'package' not in checksum:
            raise ValueError('invalid Cargo checksum: ' + name)
        for relative, expected in files.items():
            existing = checksum['files'].get(relative)
            if existing is not None and existing not in (expected['before'], expected['after']):
                raise ValueError('Cargo file checksum mismatch: ' + name + '/' + relative)
        temp = root / '.cargo-checksum.json.ember-tmp'
        if temp.exists() or temp.is_symlink():
            raise ValueError('checksum temporary path exists: ' + name)
        if state == {'before'}:
            with tempfile.TemporaryDirectory(prefix='.ember-cargo-patch-', dir=vendor) as tmp:
                staged = Path(tmp)
                for relative in files:
                    destination = staged / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    source = checked_path(root, relative)
                    if source.is_file():
                        shutil.copyfile(source, destination)
                subprocess.run([str(patch_tool), '--batch', '--forward', '--fuzz=0',
                                '--no-backup-if-mismatch', '-p1', '-i', str(patch)],
                               cwd=staged, check=True, stdout=subprocess.DEVNULL)
                for relative, expected in files.items():
                    result = checked_path(staged, relative)
                    actual = digest(result) if result.is_file() else None
                    if actual != expected['after']:
                        raise ValueError('patched bytes differ: ' + name + '/' + relative)
                for relative, expected in files.items():
                    target = checked_path(root, relative)
                    if expected['after'] is None:
                        target.unlink()
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(staged / relative, target)
        for relative, expected in files.items():
            if expected['after'] is None:
                checksum['files'].pop(relative, None)
            elif relative in checksum['files'] or expected['before'] is None:
                checksum['files'][relative] = expected['after']
        try:
            with temp.open('x') as out:
                json.dump(checksum, out, separators=(',', ':'))
                out.write('\n')
            os.replace(temp, checksum_path)
        finally:
            if temp.exists():
                temp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('vendor', 'registry', 'patch', 'prefix'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    apply(args.vendor, args.registry, args.patch, args.prefix)


if __name__ == '__main__':
    main()
