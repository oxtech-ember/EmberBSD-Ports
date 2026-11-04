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
build.require_common_v8 = build.require_common_node = build.require_common_perfetto = lambda options: None
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

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / 'work'; out = work / 'out'; out.mkdir(parents=True)
    args = out / 'args.gn'; args.write_text(build.gn_arguments({'chosen': 'old'}))
    generated = out / 'gen'; generated.mkdir()
    original = args.read_bytes(), args.stat().st_mtime_ns
    options = SimpleNamespace(work=work, sdk_source=Path('/sdk'), workspace=Path('/source'),
        ports_source=Path('/ports'), git=Path('/git'), resume_configure=False,
        retry_configure=True, perfetto_source=Path('/perfetto'), host_prefix=Path('/host'), target='target')
    build.producer_inputs = lambda *a: (SimpleNamespace(tool=lambda name: name), {},
                                        {'chosen': 'old', 'node_shared_perfetto': True})
    build.gn_source = lambda *a: work
    calls = []
    build.load_sdk = lambda *a: {'process': SimpleNamespace(run_logged=lambda *a, **kw: calls.append(kw))}
    (work / 'configure.log').write_text('previous failure')
    build.local_module = lambda *a: SimpleNamespace(atomic_json=lambda *a: None)
    for marker_name in ('build.ninja', '.ninja_log', '.ninja_deps'):
        marker = out / marker_name; marker.touch()
        try:
            build.configure(options)
            raise AssertionError('accepted ' + marker_name)
        except ValueError:
            assert (args.read_bytes(), args.stat().st_mtime_ns) == original
        marker.unlink()
    build.configure(options)
    assert args.read_text() == build.gn_arguments({'chosen': 'old', 'node_shared_perfetto': True})
    assert generated.is_dir() and calls[-1]['append'] is True
    assert (work / 'configure.log').read_text() == 'previous failure'
    unchanged = args.stat().st_mtime_ns
    build.configure(options)
    assert args.stat().st_mtime_ns == unchanged
    build.producer_inputs = lambda *a: (SimpleNamespace(tool=lambda name: name), {}, {'chosen': 'updated'})
    build.configure(options)
    assert args.read_text() == build.gn_arguments({'chosen': 'updated'})
print('PASS: retry preserves generated output, rejects Ninja and accepts verified changed inputs, and retains unchanged args')
