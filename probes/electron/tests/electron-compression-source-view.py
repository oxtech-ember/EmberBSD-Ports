#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Verify selective upstream wrapper activation and unchanged retry."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files'
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, owner/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
view = load('view', 'protobuf-source-view.py')
compression = load('compression', 'compression-source-view.py')
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); source = root/'source'; dest = root/'view'
    origin = source/'third_party'; origin.mkdir(parents=True)
    selected = dest/'src/third_party'; selected.mkdir(parents=True)
    unbundle = source/'build/linux/unbundle'; unbundle.mkdir(parents=True)
    (unbundle/'replace_gn_files.py').write_text("REPLACEMENTS = {'brotli': 'third_party/brotli/BUILD.gn', 'zstd': 'third_party/zstd/BUILD.gn'}\n")
    for name in compression.NAMES:
        component = origin/name; (component/'include').mkdir(parents=True)
        (component/'BUILD.gn').write_text('old gn')
        (component/'include'/'x.h').write_text('vendor header')
        (component/'keep').write_text('source')
        (unbundle/(name+'.gn')).write_text('shim_headers("shim") { root_path = "include"\n headers = [ "x.h" ]\n}\n')
        (selected/name).symlink_to(component, target_is_directory=True)
    neighbor = selected/'neighbor'; neighbor.write_text('preserve')
    neighbor_before = (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns)
    actual_verify = compression.verify_view
    def interrupted(*args):
        raise ValueError('interrupted after compression swap')
    with patch.object(compression, 'verify_view', side_effect=interrupted):
        try: compression.activate(view, source, dest, lambda: None)
        except ValueError as error: assert 'interrupted' in str(error)
        else: raise AssertionError('injected interruption ignored')
    marker = root/'.view.compression-components-migration'
    assert marker.is_file()
    def old_selection():
        assert all((selected/name).is_symlink() for name in compression.NAMES)
    compression.activate(view, source, dest, old_selection)
    assert not marker.exists()
    assert (neighbor.stat().st_ino, neighbor.stat().st_mtime_ns) == neighbor_before
    actual_verify(view, source, dest)
    for name in compression.NAMES:
        assert not (selected/name/'include/x.h').exists()
        assert (selected/name/'BUILD.gn').resolve() == unbundle/(name+'.gn')
    old = (selected/'brotli/BUILD.gn').lstat().st_ino
    compression.activate(view, source, dest, lambda: None)
    assert (selected/'brotli/BUILD.gn').lstat().st_ino == old
print('PASS: upstream compression wrappers mask vendored headers and retry is a no-op')
