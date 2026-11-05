#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Transactional replacement and recovery of previously projected components."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/protobuf-source-view.py'
spec = importlib.util.spec_from_file_location('view', owner)
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    origin = root/'source'; origin.mkdir()
    dest = root/'view'; selected = dest/'src/third_party'; selected.mkdir(parents=True)
    for name in ('a', 'b'):
        (selected/name).mkdir(); (selected/name/'identity').write_text('old')
        (selected/name/'payload').write_text('old-' + name)
    def check_old(path, name, partial):
        return path.is_dir() and not path.is_symlink() and (partial or (path/'identity').read_text() == 'old')
    def verify_old():
        assert all(check_old(selected/name, name, False) for name in ('a', 'b'))
    def build_new(name, path):
        path.mkdir(); (path/'identity').write_text('new'); (path/'payload').write_text('new-' + name)
    def verify_new(migration):
        assert all((selected/name/'identity').read_text() == 'new' for name in ('a', 'b'))
        return dest/'src'
    def run():
        return view.sibling_component_transaction(dest, origin, ['a', 'b'], 'identity', 'ml-components',
            verify_old, build_new, verify_new, check_old_entry=check_old, already_new=lambda: False)
    first_verify = [True]
    def fail_new(migration):
        if first_verify[0]:
            first_verify[0] = False
            raise ValueError('interrupted after swap')
        return verify_new(migration)
    try:
        view.sibling_component_transaction(dest, origin, ['a', 'b'], 'identity', 'ml-components',
            verify_old, build_new, fail_new, check_old_entry=check_old, already_new=lambda: False)
    except ValueError:
        pass
    else:
        raise AssertionError('injected failure ignored')
    assert (root/'.view.ml-components-migration').is_file()
    # The next run must verify and restore both old local directories before staging.
    def assert_restored():
        verify_old()
    def recover():
        return view.sibling_component_transaction(dest, origin, ['a', 'b'], 'identity', 'ml-components',
            assert_restored, build_new, verify_new, check_old_entry=check_old, already_new=lambda: False)
    recover()
    for name in ('a', 'b'):
        (selected/name/'identity').write_text('old')
        (selected/name/'payload').write_text('old-' + name)
    def partial_remove(path):
        old = next(iter(Path(path).iterdir()))
        (old/'payload').unlink()
        raise OSError('interrupted cleanup')
    try:
        with patch('shutil.rmtree', side_effect=partial_remove):
            run()
    except OSError:
        pass
    else:
        raise AssertionError('cleanup fault was not observed')
    assert (root/'.view.ml-components-migration').is_file()
    run()
    assert not (root/'.view.ml-components-migration').exists()
    verify_new(False)
print('PASS: projected component transaction recovers partial committed cleanup')
