#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check selected setfflags preserves other flags and resource-fork bytes."""
import argparse
import ctypes
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--setfflags', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
assert a.setfflags.is_absolute() and a.work.is_absolute()
a.work.mkdir()
fixture = a.work / 'fixture'
fixture.write_bytes(b'Finder metadata fixture\n')
lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
lib.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
lib.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
path = str(fixture).encode()
resource = b'fixture-resource-content'
buf = ctypes.create_string_buffer(resource)
assert lib.setxattr(path, b'com.apple.ResourceFork', buf, len(resource), 0, 0) == 0

def attr(name):
    buf = ctypes.create_string_buffer(4096)
    size = lib.getxattr(path, name, buf, len(buf), 0, 0)
    assert size >= 0
    return buf.raw[:size]

subprocess.run([str(a.setfflags), '-i', 'true', str(fixture)], check=True)
before = attr(b'com.apple.FinderInfo')
subprocess.run([str(a.setfflags), '-c', 'true', str(fixture)], check=True)
after = attr(b'com.apple.FinderInfo')
assert len(before) == len(after) == 32
expected = bytearray(before)
expected[8] |= 0x04  # kHasCustomIcon, big-endian Finder flags
assert after == bytes(expected) and after != before
assert attr(b'com.apple.ResourceFork') == resource
print('PASS: custom icon flag preserves other Finder metadata and resource fork')
