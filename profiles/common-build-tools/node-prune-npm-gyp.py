#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Remove only the replaced npm-bundled GYP backend from a Node source tree."""
import argparse
import json
import os
import shutil
import stat
import tarfile
import sys
from pathlib import Path


def prune(source, archive):
    root = Path(source)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ValueError('Node source root must be a canonical real directory')
    if (root / 'node.gyp').is_symlink() or not (root / 'node.gyp').is_file():
        raise ValueError('not an owned Node source tree')
    parent = root
    for part in ('deps', 'npm', 'node_modules', 'node-gyp'):
        parent = parent / part
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError('Node npm path must contain only real directories')
    package = parent / 'package.json'
    frontend = parent / 'lib/configure.js'
    if (package.is_symlink() or not package.is_file() or
            frontend.is_symlink() or not frontend.is_file() or
            (parent / 'lib').is_symlink() or not (parent / 'lib').is_dir()):
        raise ValueError('invalid npm node-gyp frontend')
    if json.loads(package.read_text()).get('name') != 'node-gyp':
        raise ValueError('unexpected npm package')
    content = frontend.read_text()
    if ('process.env.NODE_GYP_SOURCE' not in content or
            "'share/gyp'" not in content or
            "path.resolve(__dirname, '..', 'gyp', 'gyp_main.py')" in content):
        raise ValueError('npm frontend does not select the common GYP provider')
    backend = parent / 'gyp'
    if not os.path.lexists(backend):
        return
    if backend.is_symlink() or not backend.is_dir():
        raise ValueError('npm GYP backend is not a real directory')
    for name in ('pylib', 'pylib/gyp'):
        directory = backend / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('npm GYP backend has a non-directory parent')
    for name in ('gyp_main.py', 'pylib/gyp/__init__.py'):
        entry = backend / name
        if entry.is_symlink() or not entry.is_file() or not entry.resolve().is_relative_to(backend):
            raise ValueError('npm GYP backend has unexpected contents')
    expected = {}
    prefix = root.name + '/deps/npm/node_modules/node-gyp/gyp/'
    with tarfile.open(archive, 'r:*') as packed:
        for member in packed:
            if not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix):].rstrip('/')
            if not relative or any(part in ('', '.', '..') for part in relative.split('/')):
                raise ValueError('invalid archived GYP backend path')
            if relative in expected or not (member.isfile() or member.isdir()):
                raise ValueError('unsupported or duplicate archived GYP entry')
            if member.isfile():
                stream = packed.extractfile(member)
                if stream is None:
                    raise ValueError('archived GYP file is unreadable')
                expected[relative] = ('file', stream.read(), member.mode & ~0o020)
            else:
                expected[relative] = ('dir', None, member.mode & ~0o020)
    if not expected:
        raise ValueError('archive does not contain the npm GYP backend')
    actual = {}
    for item in backend.rglob('*'):
        rel = item.relative_to(backend).as_posix()
        if item.is_symlink():
            raise ValueError('GYP backend contains a symlink')
        mode = stat.S_IMODE(item.stat().st_mode) & ~0o020
        if item.is_file():
            actual[rel] = ('file', item.read_bytes(), mode)
        elif item.is_dir():
            actual[rel] = ('dir', None, mode)
        else:
            raise ValueError('GYP backend contains a special file')
    if actual != expected:
        raise ValueError('GYP backend differs from the validated archive')
    shutil.rmtree(backend)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--recipe', required=True, type=Path)
    parser.add_argument('--sdk-source', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.sdk_source / 'src'))
    from emberbsd_sdk import archive_metadata, sourceprep
    metadata, _ = archive_metadata.read_recipe(args.recipe, args.archive.name, args.source.name)
    measured = sourceprep.archive_hashes(args.archive.read_bytes())
    if any(measured[key] != metadata[key] for key in ('size', 'sha512', 'blake2s')):
        raise ValueError('Node archive differs from the selected recipe')
    prune(args.source, args.archive)


if __name__ == '__main__':
    main()
