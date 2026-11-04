#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Retry only selected Perfetto link and preserve existing source leaves."""
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); source = root / 'source'; dest = root / 'view'; selected = root / 'selected'
    (source / 'third_party/perfetto/gn').mkdir(parents=True)
    (source / 'third_party/perfetto/gn/perfetto.gni').write_text('original')
    (source / 'third_party/keep').mkdir(); (source / '.gn').write_text('keep')
    (selected / 'gn').mkdir(parents=True); (selected / 'gn/perfetto.gni').write_text('selected')
    view.create(source, None, dest)
    gn = dest / 'src/.gn'; before = (gn.stat().st_ino, gn.stat().st_mtime_ns)
    link = dest / 'src/third_party/perfetto'; old = link.readlink()
    view._refresh_leaves(source, None, dest, {'perfetto': selected})
    assert link.resolve() == selected and (gn.stat().st_ino, gn.stat().st_mtime_ns) == before
print('PASS: failed GN retry updates only selected Perfetto link')
