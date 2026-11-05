#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Conditional literal headers are masked for every GN toolchain."""
import importlib.util
from pathlib import Path
import sys
import tempfile

path = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/protobuf-source-view.py'
spec = importlib.util.spec_from_file_location('source_view', path)
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
with tempfile.TemporaryDirectory(prefix='electron-shim-masks-') as directory:
    shim = Path(directory) / 'zlib.gn'
    start = 'shim_headers("minizip_shim") {\nroot_path = "contrib"\nheaders = ["minizip/unzip.h"]\n'
    additions = 'if (is_win) { headers += ["minizip/iowin32.h"] }\n'
    mapping = {Path('BUILD.gn'): shim}
    shim.write_text(start + additions + '}\n')
    assert view.shim_masks(mapping) == {Path('contrib/minizip/unzip.h'), Path('contrib/minizip/iowin32.h')}
    for body in (
            'if (is_win) { root_path = "elsewhere" }',
            'if (is_win) { headers += computed }',
            'if (is_win) { headers += ["../escape.h"] }',
            'if (is_win) { headers += ["$computed.h"] }',
            'headers = ["replacement.h"]',
            'if (is_win) { headers += ["extra.h"] } else { headers = ["other.h"] }'):
        shim.write_text(start + body + '\n}\n')
        try: view.shim_masks(mapping)
        except ValueError: pass
        else: raise AssertionError('unsupported shim accepted: ' + body)
if len(sys.argv) == 2:
    actual = view.shim_masks({Path('BUILD.gn'): Path(sys.argv[1])})
    assert Path('zlib.h') in actual and Path('contrib/minizip/iowin32.h') in actual
print('PASS: conditional literal shims and the actual minizip header union')
