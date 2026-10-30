#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check complete, prefix-contained ts-proto provider inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('providers', owner / 'electron44/files/node-providers.py')
providers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(providers)
with tempfile.TemporaryDirectory(prefix='ts-proto-inputs-') as tmp:
    prefix = Path(tmp).resolve()
    modules = prefix / 'lib/node_modules'
    for name in ('@bufbuild/protobuf', 'case-anything', 'dprint-node', 'ts-poet', 'ts-proto', 'ts-proto-descriptors'):
        root = modules / name
        root.mkdir(parents=True)
        (root / 'package.json').write_text(json.dumps({'name': name, 'version': '1'}))
        (root / 'source.js').write_text('source')
    (modules / 'ts-proto/protoc-gen-ts_proto').write_text('entry')
    (modules / 'dprint-node/dprint-node.node').write_text('addon')
    selected = providers.select_ts_proto(modules, prefix)
    assert str(modules / '@bufbuild/protobuf/source.js') in selected
    assert str(modules / 'dprint-node/dprint-node.node') in selected
    assert str(modules / 'ts-proto/protoc-gen-ts_proto') in selected
    outside = prefix.parent / (prefix.name + '-outside')
    outside.write_text('outside')
    try:
        (modules / 'ts-poet/escape').symlink_to(outside)
        try:
            providers.select_ts_proto(modules, prefix)
            raise AssertionError('escaped provider accepted')
        except ValueError as e:
            assert 'escapes native prefix' in str(e)
    finally:
        outside.unlink()
print('ts-proto selected provider inputs: PASS')
