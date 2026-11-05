#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Migrate only verified DevTools modules and retain other source-view leaves."""
import importlib.util
import json
from unittest.mock import patch
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
view.ELECTRON_BUILD_MODULES = ('fixture',)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary); source = root / 'source'; modules = root / 'modules'; dest = root / 'view'
    (source / '.gn').parent.mkdir(parents=True); (source / '.gn').write_text('gn')
    (source / 'electron').mkdir(); (source / 'third_party/node').mkdir(parents=True)
    origin = source / 'third_party/devtools-frontend/src/node_modules'
    origin.mkdir(parents=True); (origin / 'old.js').write_text('old')
    (modules / 'fixture').mkdir(parents=True)
    (modules / 'fixture/package.json').write_text(json.dumps({'name': 'fixture'}))
    view.create(source, None, dest, node_modules=modules)
    selected = dest / 'src/third_party/devtools-frontend/src/node_modules'
    selected.unlink(); view.mirror(origin, selected)
    keep = dest / 'src/.gn'; before = (keep.stat().st_ino, keep.stat().st_mtime_ns)
    foreign = selected / 'foreign'; foreign.write_text('foreign')
    try:
        view.migrate_devtools_modules(source, None, dest, node_modules=modules)
        raise AssertionError('foreign file accepted')
    except ValueError:
        assert selected.is_dir() and not selected.is_symlink()
        assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    foreign.unlink()
    real_verify = view.verify
    def fail_after_swap(*args, **kwargs):
        if kwargs.get('_migration'):
            raise ValueError('injected verification failure')
        return real_verify(*args, **kwargs)
    view.verify = fail_after_swap
    try:
        view.migrate_devtools_modules(source, None, dest, node_modules=modules)
        raise AssertionError('injected failure ignored')
    except ValueError:
        assert selected.is_dir() and not selected.is_symlink()
        assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    view.verify = real_verify
    view.migrate_devtools_modules(source, None, dest, node_modules=modules)
    assert selected.is_symlink() and selected.resolve() == modules.resolve()
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    view.verify(source, None, dest, node_modules=modules)
    backup = root / '.view.devtools-modules-old'
    marker = root / '.view.devtools-modules-migration'
    view.mirror(origin, backup); marker.write_text('devtools-modules-v1\n')
    view.migrate_devtools_modules(source, None, dest, node_modules=modules)
    assert not backup.exists() and not marker.exists() and selected.is_symlink()
    selected.unlink(); view.mirror(origin, selected)
    def interrupted_cleanup(path):
        (Path(path) / 'old.js').unlink()
        raise OSError('injected partial cleanup')
    try:
        with patch('shutil.rmtree', side_effect=interrupted_cleanup):
            view.migrate_devtools_modules(source, None, dest, node_modules=modules)
        raise AssertionError('partial cleanup ignored')
    except OSError:
        assert marker.read_text() == 'devtools-modules-committed-v1\n'
        assert backup.is_dir() and not (backup / 'old.js').exists()
    view.migrate_devtools_modules(source, None, dest, node_modules=modules)
    assert selected.is_symlink() and not marker.exists() and not backup.exists()
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
print('PASS: verified DevTools modules migrate without replacing other leaves')

# The build guard precedes migration and survives both success and failure.
build_spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(build_spec); build_spec.loader.exec_module(build)
with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary); configuration = work / 'configuration.json'
    configuration.write_text('original')
    def check_guard(options):
        assert (work / 'reconfigure-incomplete').is_file()
        assert configuration.read_text() == 'original'
        if options == 'fail':
            raise ValueError('failure')
    build.gn_source = check_guard
    for outcome in ('ok', 'fail'):
        try:
            build.migrate_devtools_only(outcome, work)
        except ValueError:
            assert outcome == 'fail'
        assert (work / 'reconfigure-incomplete').exists()
        assert configuration.read_text() == 'original'
print('PASS: migration guard precedes changes and preserves the configuration')
