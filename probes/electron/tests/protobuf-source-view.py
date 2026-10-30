#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check Electron's common Protobuf source view and input boundaries."""
import importlib.util
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('protobuf_view', owner / 'electron44/files/protobuf-source-view.py')
view = importlib.util.module_from_spec(spec); spec.loader.exec_module(view)
with tempfile.TemporaryDirectory(prefix='electron-protobuf-view-') as temporary:
    root = Path(temporary); source = root / 'original'; protobuf = root / 'common'; output = root / 'view'
    (source / 'third_party/protobuf/src').mkdir(parents=True)
    (source / 'third_party/protobuf/third_party').mkdir()
    (source / '.gn').write_text('original')
    (source / 'third_party/protobuf/BUILD.gn').write_text('chromium build')
    (source / 'third_party/protobuf/src/old').write_text('bundled')
    (protobuf / 'src').mkdir(parents=True); (protobuf / 'third_party').mkdir()
    (protobuf / 'src/common').write_text('selected')
    actual = view.create(source, protobuf, output)
    assert view.verify(source, protobuf, output) == actual
    assert (actual / 'third_party/protobuf/src/common').read_text() == 'selected'
    assert not (actual / 'third_party/protobuf/src/old').exists()
    assert (source / 'third_party/protobuf/src/old').read_text() == 'bundled'
    assert (actual / 'third_party/protobuf/BUILD.gn').read_text() == 'chromium build'
    assert not (actual / 'out').is_symlink()
    link = actual / 'third_party/protobuf/src'; link.unlink(); link.symlink_to(source / 'third_party/protobuf/src')
    try:
        view.verify(source, protobuf, output)
        raise AssertionError('accepted different common source')
    except ValueError:
        pass
    link.unlink(); link.symlink_to(protobuf / 'src', target_is_directory=True)
    third_party = actual / 'third_party'
    moved = output / 'moved-third-party'; third_party.rename(moved)
    third_party.symlink_to(moved, target_is_directory=True)
    try:
        view.verify(source, protobuf, output)
        raise AssertionError('accepted redirected composition directory')
    except ValueError:
        pass
    try:
        view.create(source, protobuf, source / 'nested')
        raise AssertionError('accepted input overlap')
    except ValueError:
        pass
    node = root / 'node'; node.mkdir(); (node / 'node.gni').write_text('node')
    perfetto = root / 'perfetto'; (perfetto / 'gn').mkdir(parents=True)
    (perfetto / 'gn/perfetto.gni').write_text('perfetto')
    combined = root / 'combined'
    selected = view.create(source, protobuf, combined, node=node, perfetto=perfetto)
    assert view.verify(source, protobuf, combined, node=node, perfetto=perfetto) == selected
    assert (selected / 'third_party/electron_node/node.gni').read_text() == 'node'
    assert (selected / 'third_party/perfetto/gn/perfetto.gni').read_text() == 'perfetto'
    (source / 'v8').mkdir(); (source / 'v8/BUILD.gn').write_text('old')
    v8 = root / 'v8-common'; (v8 / 'include').mkdir(parents=True)
    (v8 / 'BUILD.gn').write_text('new'); (v8 / 'include/v8-version.h').write_text('version')
    v8_output = root / 'v8-view'
    v8_root = view.create(source, protobuf, v8_output, node=node, perfetto=perfetto, v8=v8)
    assert view.verify(source, protobuf, v8_output, node=node, perfetto=perfetto, v8=v8) == v8_root
    assert (v8_root / 'v8/BUILD.gn').read_text() == 'new'
    assert (source / 'v8/BUILD.gn').read_text() == 'old'
    (v8_root / 'v8').unlink(); (v8_root / 'v8').symlink_to(source / 'v8', target_is_directory=True)
    try:
        view.verify(source, protobuf, v8_output, node=node, perfetto=perfetto, v8=v8)
        raise AssertionError('accepted changed V8 source link')
    except ValueError:
        pass
    node_only = root / 'node-only'
    node_root = view.create(source, None, node_only, node=node)
    assert view.verify(source, None, node_only, node=node) == node_root
    assert (node_root / 'third_party/protobuf/src/old').read_text() == 'bundled'
    selected_node = selected / 'third_party/electron_node'; selected_node.unlink()
    selected_node.symlink_to(perfetto, target_is_directory=True)
    try:
        view.verify(source, protobuf, combined, node=node, perfetto=perfetto)
        raise AssertionError('accepted changed Node source link')
    except ValueError:
        pass
print('PASS: common Protobuf view, unchanged original and tamper/overlap controls')
