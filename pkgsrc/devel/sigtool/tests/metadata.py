#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Sign a real Mach-O and check native resource and metadata preservation."""
import argparse
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def xattr(path, name, value=None):
    libc = ctypes.CDLL(None, use_errno=True)
    path, name = os.fsencode(path), name.encode()
    if value is None:
        libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
        libc.getxattr.restype = ctypes.c_ssize_t
        size = libc.getxattr(path, name, None, 0, 0, 0)
        if size < 0:
            raise OSError(ctypes.get_errno(), 'getxattr failed')
        buf = ctypes.create_string_buffer(size)
        if libc.getxattr(path, name, buf, size, 0, 0) != size:
            raise OSError(ctypes.get_errno(), 'getxattr failed')
        return buf.raw
    libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    buf = ctypes.create_string_buffer(value)
    if libc.setxattr(path, name, buf, len(value), 0, 0):
        raise OSError(ctypes.get_errno(), 'setxattr failed')
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('codesign', 'allocate', 'rez', 'icon', 'input', 'work-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    codesign, allocate, rez, icon, fixture, work = (getattr(args, name).resolve(strict=True)
        for name in ('codesign', 'allocate', 'rez', 'icon', 'input', 'work_dir'))
    with tempfile.TemporaryDirectory(prefix='sigtool-metadata-', dir=work) as tmp:
        for mode in (0o751, 0o555):
            target = Path(tmp) / ('input-' + str(mode))
            shutil.copyfile(fixture, target)
            subprocess.run([str(rez), '--input-format=text', '--resource-fork-only', '--append',
                            str(icon), '-o', str(target)], check=True)
            finder = bytearray(32)
            finder[8:10] = (0x4000).to_bytes(2, 'big')
            xattr(target, 'com.apple.FinderInfo', bytes(finder))
            xattr(target, 'org.emberbsd.sigtool-test', b'preserve me')
            before = {name: xattr(target, name) for name in ('com.apple.ResourceFork',
                       'com.apple.FinderInfo', 'org.emberbsd.sigtool-test')}
            target.chmod(mode)
            env = dict(os.environ, CODESIGN_ALLOCATE=str(allocate))
            subprocess.run([str(codesign), '--force', '-s', '-', str(target)], env=env, check=True)
            for name, expected in before.items():
                if xattr(target, name) != expected:
                    raise RuntimeError('source metadata changed: ' + name)
            if stat.S_IMODE(target.stat().st_mode) != mode:
                raise RuntimeError('source mode was not preserved')
        target = Path(tmp) / 'immutable-input'
        shutil.copyfile(fixture, target)
        before = hashlib.sha256(target.read_bytes()).digest()
        libc = ctypes.CDLL(None, use_errno=True)
        libc.chflags.argtypes = [ctypes.c_char_p, ctypes.c_uint]
        if libc.chflags(os.fsencode(target), 2):  # Darwin UF_IMMUTABLE
            raise OSError(ctypes.get_errno(), 'cannot set test file flag')
        try:
            entries = set(Path(tmp).iterdir())
            result = subprocess.run([str(codesign), '--force', '-s', '-', str(target)],
                env=dict(os.environ, CODESIGN_ALLOCATE=str(allocate)), text=True, capture_output=True)
            if result.returncode == 0 or 'flags that prevent replacement' not in result.stderr:
                raise RuntimeError('immutable input was not rejected')
            if set(Path(tmp).iterdir()) != entries or hashlib.sha256(target.read_bytes()).digest() != before:
                raise RuntimeError('immutable failure changed input or left temporary files')
        finally:
            if libc.chflags(os.fsencode(target), 0):
                raise OSError(ctypes.get_errno(), 'cannot clear test file flag')
    print('PASS: signed Mach-O preserves metadata and rejects immutable input')


if __name__ == '__main__':
    main()
