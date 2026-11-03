#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Install the successful Electron producer output into a pkgsrc DESTDIR.

The package build phase owns source and toolchain validation. This separate
installation phase never invokes GN/Ninja or accepts an external archive path.
"""
import argparse
import importlib
import importlib.util
import os
from pathlib import Path, PurePosixPath
import stat
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def stage_owner():
    spec = importlib.util.spec_from_file_location('electron_runtime_stage',
        Path(__file__).with_name('stage-runtime.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def destination_root(destdir, prefix):
    destdir = Path(destdir)
    require(destdir.is_absolute() and destdir != Path('/'),
            'use an absolute package DESTDIR, not the live root')
    require('..' not in destdir.parts, 'DESTDIR contains traversal')
    require(prefix == '/usr/pkg',
            'the selected Electron target dependency layout requires PREFIX=/usr/pkg')
    # Refuse a redirected staging parent rather than installing through it.
    current = Path(destdir.anchor)
    for part in destdir.parts[1:]:
        current /= part
        require(stat.S_ISDIR(os.lstat(current).st_mode),
                'DESTDIR must have only real directory parents: ' + str(current))
    return destdir / prefix.lstrip('/')


def package_directory(root, relative, *, create=False):
    current = root
    for part in PurePosixPath(relative).parts:
        current /= part
        if create:
            try:
                current.mkdir()
            except FileExistsError:
                pass
        require(stat.S_ISDIR(os.lstat(current).st_mode),
                'package destination parent is not a real directory: ' + str(current))
    return current


def install(work, destdir, prefix, target, sdk, owner):
    paths = sdk[0]
    work = Path(work)
    require(work.is_absolute(), 'producer work must be absolute')
    paths.real_directory(work)
    paths.real_directory(work / 'out')
    paths.reject_overlap(work, destdir)
    destination_root(destdir, prefix)
    # Check all existing destination components before touching either output.
    lib = package_directory(Path(destdir), 'usr/pkg/lib', create=True)
    binary = package_directory(Path(destdir), 'usr/pkg/bin', create=True) / 'electron'
    runtime = lib / 'electron44'
    require(not os.path.lexists(runtime) and not os.path.lexists(binary),
            'Electron package destinations must be new')
    facts = owner.stage_producer_runtime(work, runtime, target=target, sdk=sdk)
    # No replacement: a concurrent name remains untouched. A failure leaves
    # this package's staged payload for diagnosis; no installed package exists.
    os.symlink('../lib/electron44/electron', binary)
    return facts


def plist(destdir, prefix):
    root = destination_root(destdir, prefix)
    runtime = package_directory(Path(destdir), 'usr/pkg/lib/electron44')
    binary = package_directory(Path(destdir), 'usr/pkg/bin') / 'electron'
    require(binary.is_symlink() and os.readlink(binary) == '../lib/electron44/electron',
            'installed Electron link differs')
    rows = ['bin/electron']
    def fail(error):
        raise error
    for parent, directories, files in os.walk(runtime, followlinks=False, onerror=fail):
        directory = Path(parent)
        if not directories and not files:
            rows.append('@pkgdir ' + directory.relative_to(root).as_posix())
        for name in directories + files:
            path = directory / name
            kind = stat.S_IFMT(os.lstat(path).st_mode)
            require(kind in (stat.S_IFDIR, stat.S_IFREG, stat.S_IFLNK),
                    'special file in installed payload: ' + str(path))
            if kind != stat.S_IFDIR:
                rows.append(path.relative_to(root).as_posix())
    return sorted(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'plist'))
    for name in ('sdk-source', 'work', 'destdir', 'lock-root'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--target', required=True, choices=('amd64', 'aarch64'))
    args = parser.parse_args()
    for name in ('sdk_source', 'work', 'destdir', 'lock_root'):
        require(getattr(args, name).is_absolute(), name + ' must be absolute')
    owner = stage_owner()
    sdk = owner.load_sdk(args.sdk_source)
    process = importlib.import_module('emberbsd_sdk.process')
    require(Path(process.__file__).resolve() == args.sdk_source.resolve() / 'src/emberbsd_sdk/process.py',
            'selected SDK process module origin differs')
    contexts = sorted({str(path.resolve()) for path in (args.work, args.destdir)})
    with process.ContextLocks(contexts, str(args.lock_root),
                              shared=args.action == 'plist'):
        with process.ContextLocks([str(args.sdk_source.resolve())], str(args.lock_root), shared=True):
            if args.action == 'install':
                install(args.work, args.destdir, args.prefix, args.target, sdk, owner)
            else:
                print('\n'.join(plist(args.destdir, args.prefix)))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        sys.exit('Electron package installation failed: ' + str(error))
