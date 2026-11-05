#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Existing component links migrate transactionally without replacing the view."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('view', owner / '../../pkgsrc/devel/electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary).resolve(); source = root / 'source'; dest = root / 'view'; common = root / 'common'
    source.mkdir(); (source / '.gn').write_text('gn'); third = source / 'third_party'; third.mkdir()
    for name in ('abseil-cpp', 'icu', 're2', 'protobuf'):
        path = third / name; path.mkdir(); (path / 'BUILD.gn').write_text('old')
    (common / 'src').mkdir(parents=True); (common / 'third_party').mkdir()
    shim = root / 'shim'; shim.write_text('new')
    view.abseil_replacements = view.icu_replacements = view.re2_replacements = lambda source: {Path('BUILD.gn'): shim}
    view.abseil_masks = lambda *args: frozenset()
    view.shim_masks = lambda *args: frozenset()
    view.create(source, None, dest)
    keep = dest / 'src/.gn'; before = (keep.stat().st_ino, keep.stat().st_mtime_ns)
    opts = dict(system_abseil=True, system_icu=True, system_re2=True)
    real_verify = view.verify
    def interrupted(*args, **kwargs):
        if kwargs.get('_migration'):
            raise ValueError('injected failure after swap')
        return real_verify(*args, **kwargs)
    view.verify = interrupted
    try:
        view.activate_common_components(source, common, dest, **opts)
        raise AssertionError('injected failure ignored')
    except ValueError:
        pass
    view.verify = real_verify
    view.activate_common_components(source, common, dest, **opts)
    for name in ('abseil-cpp', 'icu', 're2', 'protobuf'):
        assert (dest / 'src/third_party' / name).is_dir() and not (dest / 'src/third_party' / name).is_symlink()
    assert (keep.stat().st_ino, keep.stat().st_mtime_ns) == before
    view.verify(source, common, dest, **opts)
    second = root / 'second'; view.create(source, None, second)
    foreign = second / 'src/third_party/icu'; foreign.unlink(); foreign.symlink_to(root)
    try:
        view.activate_common_components(source, common, second, **opts)
        raise AssertionError('foreign old link accepted')
    except ValueError:
        assert (second / 'src/third_party/abseil-cpp').is_symlink()
    foreign.unlink(); foreign.symlink_to(third / 'icu', target_is_directory=True)
    def interrupted_cleanup(path):
        entry = next(iter(Path(path).iterdir())); entry.unlink()
        raise OSError('partial cleanup')
    try:
        with patch('shutil.rmtree', side_effect=interrupted_cleanup):
            view.activate_common_components(source, common, second, **opts)
        raise AssertionError('partial cleanup ignored')
    except OSError:
        assert (root / '.second.common-components-migration').is_file()
    view.activate_common_components(source, common, second, **opts)
    assert not (root / '.second.common-components-migration').exists()
    view.verify(source, common, second, **opts)
    third_view = root / 'third-view'; view.create(source, None, third_view)
    original_dependency_view = view.dependency_view
    calls = [0]
    def interrupted_stage(*args, **kwargs):
        calls[0] += 1
        result = original_dependency_view(*args, **kwargs)
        if calls[0] == 1:
            raise OSError('injected staging failure')
        return result
    view.dependency_view = interrupted_stage
    try:
        view.activate_common_components(source, common, third_view, **opts)
        raise AssertionError('staging failure ignored')
    except OSError:
        assert (root / '.third-view.common-components-migration').is_file()
        assert (third_view / 'src/third_party/abseil-cpp').is_symlink()
    view.dependency_view = original_dependency_view
    view.activate_common_components(source, common, third_view, **opts)
    assert not (root / '.third-view.common-components-migration').exists()
    view.verify(source, common, third_view, **opts)
print('PASS: 4 common views recover after interrupted swap, retaining other leaves')
