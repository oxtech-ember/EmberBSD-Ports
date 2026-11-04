#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Reject incompatible or completed initial GN work without changing it."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
build.require_common_v8 = build.require_common_node = lambda options: None
build.load_sdk = lambda source: {}
build.verify_source = lambda *args: None
build.producer_inputs = lambda *args: (None, {}, {'chosen': 'new'})
prepared = []
build.prepare_build_inputs = lambda *args: prepared.append(True)
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / 'work'; out = work / 'out'; out.mkdir(parents=True)
    args = out / 'args.gn'; args.write_text(build.gn_arguments({'chosen': 'old'}))
    options = SimpleNamespace(work=work, sdk_source=Path('/sdk'), workspace=Path('/source'),
                              ports_source=Path('/ports'), git=Path('/git'), resume_configure=True)
    before = args.read_bytes(), args.stat().st_mtime_ns
    for mode in ('changed-args', 'gn-output', 'completed'):
        marker = None
        if mode == 'gn-output':
            marker = out / 'build.ninja'; marker.touch()
        elif mode == 'completed':
            marker = work / 'configuration.json'; marker.touch()
        try:
            build.configure(options)
            raise AssertionError('accepted ' + mode)
        except ValueError:
            assert (args.read_bytes(), args.stat().st_mtime_ns) == before
            assert not prepared, 'prepared inputs before rejecting resume'
        if marker:
            assert marker.exists()
            marker.unlink()
print('PASS: initial configure rejects incompatible args and existing GN output')
