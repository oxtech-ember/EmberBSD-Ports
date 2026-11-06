#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise verified source refresh and selected root boundaries."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'pkgsrc/devel/electron44/files/build-electron.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with TemporaryDirectory() as directory:
    root = Path(directory).resolve()
    node, perfetto, protobuf = (root / x for x in ('node', 'perfetto', 'protobuf'))
    for p in (node, perfetto, protobuf / 'src', protobuf / 'third_party'):
        p.mkdir(parents=True, exist_ok=True)
    (node / 'emberbsd-prepared-source.json').write_text('{}')
    view = root / 'work/source-view/src/third_party'
    (view / 'protobuf').mkdir(parents=True)
    (view / 'perfetto').symlink_to(perfetto)
    for name in ('src', 'third_party'):
        (view / 'protobuf' / name).symlink_to(protobuf / name)
    options = SimpleNamespace(node_source=node, perfetto_source=perfetto, protobuf_source=protobuf)
    args = {'emberbsd_node_source_identity': str(node / 'emberbsd-prepared-source.json'),
            'v8_prepared_source_receipt': '//v8/emberbsd-prepared-source.json',
            'v8_version_hash_salt_files': [], 'v8_version_hash_salt': ''}
    keys = ['EMBERBSD_' + n + '_SOURCE_SHA256' for n in ('NODE', 'V8', 'PERFETTO', 'PROTOBUF')]
    old = dict.fromkeys(keys, 'a' * 64)
    new = dict.fromkeys(keys, 'b' * 64)
    assert m.verified_common_source_refresh(args, args, old, new, options, root / 'work') == set(keys)
    assert not m.verified_common_source_refresh(args, args, old, old, options, root / 'work')
    replacement = root / 'new-node'
    replacement.mkdir()
    (replacement / 'emberbsd-prepared-source.json').write_text('{}')
    moved_args = dict(args, emberbsd_node_source_identity=str(replacement / 'emberbsd-prepared-source.json'))
    moved = SimpleNamespace(node_source=replacement, perfetto_source=perfetto, protobuf_source=protobuf)
    assert m.verified_common_source_refresh(args, moved_args, old, old, moved, root / 'work') == {keys[0]}
    bad = dict(new, EMBERBSD_PERFETTO_SOURCE_SHA256='bad')
    for env, opt in ((bad, options), (new, SimpleNamespace(node_source=node, perfetto_source=node, protobuf_source=protobuf))):
        try:
            m.verified_common_source_refresh(args, args, old, env, opt, root / 'work')
        except ValueError:
            pass
        else:
            raise AssertionError('invalid identity or changed source root accepted')
print('PASS: verified common source refresh and source root boundaries')
