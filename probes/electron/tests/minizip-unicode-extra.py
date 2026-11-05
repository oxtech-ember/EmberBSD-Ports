#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the selected compatibility library and Chromium ZIP extra parser."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
import zlib
p = argparse.ArgumentParser()
p.add_argument('--cxx', required=True)
p.add_argument('--compat-include', type=Path, required=True)
p.add_argument('--helper-include', type=Path, required=True)
p.add_argument('--zlib-include', type=Path, required=True)
p.add_argument('--zlib-libdir', type=Path, required=True)
p.add_argument('--library', type=Path, required=True)
p.add_argument('--sysroot', type=Path)
p.add_argument('--macos-minimum')
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix='minizip-unicode-test-') as td:
    root = Path(td)
    def field(raw, name, valid=True, version=1):
        payload = bytes([version]) + struct.pack('<I', zlib.crc32(raw) ^ (0 if valid else 1)) + name
        return struct.pack('<HH', 0x7075, len(payload)) + payload
    def make(name, filename, extra, replacement=None):
        info = zipfile.ZipInfo(filename); info.extra = extra
        path = root / (name + '.zip')
        with zipfile.ZipFile(path, 'w') as z: z.writestr(info, b'payload')
        if replacement: path.write_bytes(path.read_bytes().replace(*replacement))
        return path
    cases = []
    for n, raw, effective in [('physical-unsafe', '../evil.txt', 'safe.txt'),
                              ('effective-unsafe', 'safe.txt', '../evil.txt'),
                              ('unicode', 'plain.txt', 'имя.txt')]:
        raw_bytes = raw.encode(); cases.append((make(n, raw, field(raw_bytes, effective.encode())), raw, effective, 'ok'))
    raw=b'physical'
    cases += [(make('duplicate', 'physical', field(raw,b'first')+field(raw,b'last')), 'physical', 'last', 'ok'),
              (make('invalid-crc', 'physical', field(raw,b'first')+field(raw,b'wrong',False)), 'physical', 'first', 'ok'),
              (make('wrong-version', 'physical', field(raw,b'wrong',True,2)), 'physical', '', 'ok'),
              (make('short-field', 'physical', struct.pack('<HH',0x7075,3)+b'\1ab'), 'physical', '', 'bad'),
              (make('truncated-tail', 'physical', field(raw,b'first')+b'\x11\x22'), 'physical', '', 'bad')]
    raw = b'a' * 65535
    cases.append((make('max-name', raw.decode(), field(raw,b'safe')), 'MAXNAME', 'safe', 'ok'))
    raw=b'aa\0bb'
    cases.append((make('embedded-nul', 'aaXbb', field(raw,b'safe'), (b'aaXbb',raw)), 'NULNAME', 'safe', 'ok'))
    cmd=[a.cxx, '-std=c++20', '-fno-exceptions', '-fno-rtti', '-Werror=unsafe-buffer-usage',
         '-I'+str(a.compat_include), '-I'+str(a.helper_include), '-I'+str(a.zlib_include)]
    if a.sysroot: cmd += ['-isysroot',str(a.sysroot)]
    if a.macos_minimum: cmd += ['-mmacos-version-min='+a.macos_minimum]
    cmd += [str(Path(__file__).with_suffix('.cc')),str(a.library),'-L'+str(a.zlib_libdir),'-lz',
            '-Wl,-rpath,'+str(a.library.parent),'-o',str(root/'verify')]
    subprocess.run(cmd,check=True)
    for path, raw, effective, result in cases:
        subprocess.run([str(root/'verify'),str(path),raw,effective,result],check=True)
print('PASS: selected compat central fields, CRC/bounds, physical and effective names')
