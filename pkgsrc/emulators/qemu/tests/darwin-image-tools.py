#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check QEMU's patched Darwin build and install image-tool paths.

Use a real Mach-O input, the QEMU icon and HVF entitlement plist, and a
pkgsrc-patched entitlement.sh whose tool paths have already been substituted.
The selected PATH must contain the SDK utilities used by that script.
"""
import argparse
import ctypes
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile


def check_signature(path, expected_entitlements):
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    security = ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security')
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                          ctypes.c_long, ctypes.c_bool]
    cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    security.SecStaticCodeCreateWithPath.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                     ctypes.POINTER(ctypes.c_void_p)]
    security.SecStaticCodeCheckValidity.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                    ctypes.c_void_p]
    security.SecCodeCopySigningInformation.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                        ctypes.POINTER(ctypes.c_void_p)]
    cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    cf.CFDictionaryGetValue.restype = ctypes.c_void_p
    cf.CFPropertyListCreateData.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.c_long, ctypes.c_ulong,
                                            ctypes.POINTER(ctypes.c_void_p)]
    cf.CFPropertyListCreateData.restype = ctypes.c_void_p
    cf.CFDataGetLength.argtypes = [ctypes.c_void_p]
    cf.CFDataGetLength.restype = ctypes.c_long
    cf.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
    cf.CFDataGetBytePtr.restype = ctypes.c_void_p
    raw = os.fsencode(path)
    url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
    if not url:
        raise RuntimeError('cannot create a code URL')
    code = ctypes.c_void_p()
    try:
        status = security.SecStaticCodeCreateWithPath(url, 0, ctypes.byref(code))
        if status or not code.value:
            raise RuntimeError(f'cannot open signed code: {status}')
        status = security.SecStaticCodeCheckValidity(code, 0, None)
        if status:
            raise RuntimeError(f'code signature verification failed: {status}')
        info = ctypes.c_void_p()
        status = security.SecCodeCopySigningInformation(code, 2, ctypes.byref(info))
        if status or not info.value:
            raise RuntimeError(f'cannot inspect signing information: {status}')
        try:
            key = ctypes.c_void_p.in_dll(security, 'kSecCodeInfoEntitlementsDict')
            entitlements = cf.CFDictionaryGetValue(info, key)
            if not entitlements:
                raise RuntimeError('signed code has no entitlements')
            data = cf.CFPropertyListCreateData(None, entitlements, 100, 0, None)
            if not data:
                raise RuntimeError('cannot serialize signed entitlements')
            try:
                actual = plistlib.loads(ctypes.string_at(cf.CFDataGetBytePtr(data),
                                                         cf.CFDataGetLength(data)))
            finally:
                cf.CFRelease(data)
            if actual != expected_entitlements or actual.get('com.apple.security.hypervisor') is not True:
                raise RuntimeError('signed executable has incorrect entitlements')
        finally:
            cf.CFRelease(info)
    finally:
        if code.value:
            cf.CFRelease(code)
        cf.CFRelease(url)


def get_xattr(path, name):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    libc.getxattr.restype = ctypes.c_ssize_t
    target, key = os.fsencode(path), name.encode()
    size = libc.getxattr(target, key, None, 0, 0, 0)
    if size < 0:
        raise OSError(ctypes.get_errno(), 'getxattr failed', str(path))
    data = ctypes.create_string_buffer(size)
    if libc.getxattr(target, key, data, size, 0, 0) != size:
        raise OSError(ctypes.get_errno(), 'getxattr failed', str(path))
    return data.raw


def set_xattr(path, name, data):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    libc.setxattr.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(bytes(data))
    if libc.setxattr(os.fsencode(path), name.encode(), buffer, len(data), 0, 0):
        raise OSError(ctypes.get_errno(), 'setxattr failed', str(path))


def check_output(path, expected_entitlements, original_flags=None):
    fork = get_xattr(path, 'com.apple.ResourceFork')
    if b'icns' not in fork:
        raise RuntimeError('QEMU icon resource is missing')
    info = get_xattr(path, 'com.apple.FinderInfo')
    if len(info) != 32:
        raise RuntimeError('unexpected FinderInfo size')
    flags = int.from_bytes(info[8:10], 'big')
    if not flags & 0x0400:
        raise RuntimeError('custom icon flag is missing')
    if original_flags is not None and flags & ~0x0400 != original_flags & ~0x0400:
        raise RuntimeError('other Finder flags changed')
    check_signature(path, expected_entitlements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('shell', 'script', 'fixture', 'icon', 'entitlements', 'work-dir', 'tools-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    shell, script, fixture, icon, entitlements, work, tools = (
        getattr(args, name).resolve(strict=True) for name in
        ('shell', 'script', 'fixture', 'icon', 'entitlements', 'work_dir', 'tools_dir'))
    expected = plistlib.loads(entitlements.read_bytes())
    original = hashlib.sha256(fixture.read_bytes()).digest()
    env = dict(os.environ, PATH=str(tools), TMPDIR=str(work))
    with tempfile.TemporaryDirectory(prefix='qemu-darwin-image-', dir=work) as tmp:
        root = Path(tmp)
        output = root / 'build-output'
        subprocess.run([str(shell), str(script), str(output), str(fixture), str(icon),
                        str(entitlements)], env=env, check=True)
        check_output(output, expected)
        if hashlib.sha256(fixture.read_bytes()).digest() != original:
            raise RuntimeError('build mode changed the source executable')
        bindir = root / 'install/bin'
        bindir.mkdir(parents=True)
        unsigned = bindir / 'qemu-unsigned'
        shutil.copyfile(fixture, unsigned)
        initial_info = bytearray(32)
        initial_info[8:10] = (0x4000).to_bytes(2, 'big')
        set_xattr(unsigned, 'com.apple.FinderInfo', initial_info)
        env['MESON_INSTALL_DESTDIR_PREFIX'] = str(root / 'install')
        subprocess.run([str(shell), str(script), '--install', 'bin/qemu', 'bin/qemu-unsigned',
                        str(icon), str(entitlements)], env=env, check=True)
        check_output(bindir / 'qemu', expected, 0x4000)
    print('PASS: Darwin QEMU build and install image-tool paths')


if __name__ == '__main__':
    main()
