#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Explicit host test for an already built minizip-ng compatibility library."""
import argparse
import io
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
p = argparse.ArgumentParser()
p.add_argument('--cc', required=True)
p.add_argument('--include', required=True, type=Path)
p.add_argument('--zlib-include', required=True, type=Path)
p.add_argument('--library', required=True, type=Path)
p.add_argument('--sysroot', type=Path)
p.add_argument('--macos-minimum')
a = p.parse_args()
here = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='minizip-compat-test-') as td:
    root = Path(td)
    names = ('ioapi_test','fill_partial_test','fill_write_test','fill_offsets_test','fill32_test','fill_memstream_test')
    for name in names:
        cmd = [a.cc, '-I' + str(a.include), '-I' + str(a.zlib_include)]
        if a.sysroot:
            cmd += ['-isysroot', str(a.sysroot)]
        if a.macos_minimum:
            cmd += ['-mmacos-version-min=' + a.macos_minimum]
        cmd += [str(here / (name + '.c')), str(a.library),
                '-Wl,-rpath,' + str(a.library.parent), '-o', str(root / name)]
        subprocess.run(cmd, check=True)
    prefix = b'EMBERVIEW-MODEL-PREFIX' * 7
    for compression, name in ((zipfile.ZIP_STORED, 'stored'), (zipfile.ZIP_DEFLATED, 'deflated')):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=compression) as z:
            z.writestr('assets/тест.txt', b'test model metadata content' * 8)
        data = prefix + buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            entry = z.infolist()[0]
        header = struct.unpack_from('<IHHHHHIIIHH', data, entry.header_offset)
        offset = entry.header_offset + 30 + header[-2] + header[-1]
        path = root / (name + '.zip'); path.write_bytes(data)
        subprocess.run([str(root / 'ioapi_test'), str(path), str(offset)], check=True)
    stored = root / 'stored.zip'
    for test in ('fill_partial_test','fill32_test'):
        subprocess.run([str(root / test), str(stored)], check=True)
    for test in ('fill_write_test','fill_memstream_test'):
        path = root / (test + '.zip')
        subprocess.run([str(root / test), str(path)], check=True)
        with zipfile.ZipFile(path) as z:
            assert z.read('a') == b'abc'
    sparse = root / 'sparse'
    subprocess.run([str(root / 'fill_offsets_test'), str(sparse)], check=True)
print('PASS: compat custom I/O, partial/default callbacks, offsets and ZIP content')
