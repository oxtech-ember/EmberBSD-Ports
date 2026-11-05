#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise atomic addition and recovery of newly prepared source leaves."""
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); source = root / 'source'; dest = root / 'view'
    source.mkdir(); dest.mkdir(); (dest / 'src').mkdir()
    (source / 'keep').write_text('keep'); (dest / 'src/keep').write_text('keep')
    def verify(source, protobuf, destination, *, _updates, _refresh, **kwargs):
        view.mirror(source, destination / 'src', verify=True, updates=_updates)
    view.verify = verify
    keep = dest / 'src/keep'; identity = (keep.stat().st_ino, keep.stat().st_mtime_ns)
    (source / 'new').write_text('new')
    view._refresh_leaves(source, None, dest, {})
    assert (dest / 'src/new').read_text() == 'new'
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == identity
    (source / 'next').write_text('next'); (source / 'last').write_text('last')
    real_link = view.os.link; calls = []
    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2: raise OSError('injected failure')
        return real_link(*args, **kwargs)
    view.os.link = fail_second
    try:
        try: view._refresh_leaves(source, None, dest, {})
        except OSError: pass
        else: raise AssertionError('injected failure accepted')
    finally: view.os.link = real_link
    assert not (dest / 'src/next').exists() and not (dest / 'src/last').exists()
    marker = view._refresh_marker(dest); marker.write_text('source-view-leaves-v1\n')
    view._refresh_leaves(source, None, dest, {})
    assert not marker.exists() and (dest / 'src/next').read_text() == 'next'
    (source / 'race').write_text('race')
    def appear(*args, **kwargs):
        (dest / 'src/race').write_text('foreign')
        return real_link(*args, **kwargs)
    view.os.link = appear
    try:
        try: view._refresh_leaves(source, None, dest, {})
        except FileExistsError: pass
        else: raise AssertionError('appearing leaf accepted')
    finally: view.os.link = real_link
    assert (dest / 'src/race').read_text() == 'foreign'
    (dest / 'src/race').unlink()
    (source / 'keep').write_text('updated')
    view._refresh_leaves(source, None, dest, {})
    assert keep.read_text() == 'updated' and (dest / 'src/race').read_text() == 'race'
print('PASS: additive leaves preserve existing files, roll back, recover and refuse races')
