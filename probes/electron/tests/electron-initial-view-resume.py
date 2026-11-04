#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise interrupted initial mirror recovery without replacing ready leaves."""
import importlib.util
import json
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
view.ELECTRON_BUILD_MODULES = ('fixture',)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary); source = root / 'source'; modules = root / 'modules'; dest = root / 'view'
    (source / 'third_party/node').mkdir(parents=True)
    (source / 'electron').mkdir()
    (source / '.gn').write_text('gn')
    (source / 'electron/keep').write_text('keep')
    (source / 'third_party/node/keep').write_text('node')
    provider = root / 'node-provider'; provider.mkdir(); (provider / 'node.gni').write_text('node')
    (modules / 'fixture').mkdir(parents=True)
    manifest = modules / 'fixture/package.json'
    manifest.write_text(json.dumps({'name': 'fixture'}))
    missing = root / 'missing'
    manifest.unlink()
    try:
        view.create(source, None, missing, node=provider, node_modules=modules)
        raise AssertionError('missing module accepted')
    except ValueError:
        assert not missing.exists()
    manifest.write_text(json.dumps({'name': 'fixture'}))
    original = view.electron_module_view
    def interrupt(*args, **kwargs):
        raise ValueError('simulated interruption after mirror')
    view.electron_module_view = interrupt
    try:
        view.create(source, None, dest, node=provider, node_modules=modules)
        raise AssertionError('interruption failed')
    except ValueError:
        pass
    view.electron_module_view = original
    ready = dest / 'src/electron/keep'; before = ready.stat().st_mtime_ns
    assert not (dest / 'src/electron/node_modules').exists()
    manifest.unlink()
    try:
        view.complete_initial(source, None, dest, node=provider, node_modules=modules)
        raise AssertionError('missing module accepted on resume')
    except ValueError:
        assert not (dest / 'src/electron/node_modules').exists()
        assert ready.stat().st_mtime_ns == before
    manifest.write_text(json.dumps({'name': 'fixture'}))
    link = dest / 'src/third_party/node/node_modules'
    link.unlink(); link.symlink_to(root, target_is_directory=True)
    try:
        view.complete_initial(source, None, dest, node=provider, node_modules=modules)
        raise AssertionError('changed provider link accepted')
    except ValueError:
        assert not (dest / 'src/electron/node_modules').exists()
        assert ready.stat().st_mtime_ns == before
    link.unlink(); link.symlink_to(modules.resolve(), target_is_directory=True)
    foreign = dest / 'src/third_party/unexpected'; foreign.write_text('foreign')
    try:
        view.complete_initial(source, None, dest, node=provider, node_modules=modules)
        raise AssertionError('foreign leaf accepted')
    except ValueError:
        assert not (dest / 'src/electron/node_modules').exists()
        assert ready.stat().st_mtime_ns == before
    foreign.unlink()
    view.complete_initial(source, None, dest, node=provider, node_modules=modules)
    assert ready.stat().st_mtime_ns == before
    assert (dest / 'src/electron/node_modules/fixture').resolve() == (modules / 'fixture').resolve()
    assert (dest / 'src/third_party/electron_node').resolve() == provider.resolve()
print('PASS: initial partial view resumes only missing components')
