#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise Node's selected V8 embedder define through GYP on different prepared trees."""
import argparse
import ast
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node-source', type=Path, required=True)
parser.add_argument('--gyp', type=Path, required=True)
args = parser.parse_args()
source = args.node_source.resolve(strict=True)
gyp = args.gyp.resolve(strict=True)
files = source / 'tools/v8_gypfiles'
features = ast.literal_eval((files / 'features.gypi').read_text())
[[condition, definition]] = [pair for pair in features['target_defaults']['conditions']
                             if pair[0] == 'v8_embedder_string!=""']
embedder = ast.literal_eval((source / 'common.gypi').read_text())['variables']['v8_embedder_string']
with tempfile.TemporaryDirectory(prefix='node-embedder-') as directory:
    work = Path(directory)
    v8 = work / 'selected V8'
    v8.mkdir()
    shutil.copy2(files / 'ember_inspector_inputs.py', work)
    probe = work / 'probe.gyp'
    probe.write_text(repr({'variables': {'V8_ROOT': str(v8), 'v8_embedder_string': embedder},
                           'target_defaults': {'conditions': [[condition, definition]]},
                           'targets': [{'target_name': 'probe', 'type': 'none'}]}))
    receipt = v8 / 'emberbsd-prepared-source.json'
    record = {'format': 'emberbsd-prepared-source', 'version': 1, 'package': 'lang/v8'}
    def generate():
        receipt.write_text(json.dumps(record))
        return subprocess.run([str(gyp), '-f', 'gypd', '--depth=.', probe.name], cwd=work,
                              text=True, capture_output=True)
    for digest in ('0123456789abcdef' * 4, 'f' * 64):
        record['tree_sha256'] = digest
        result = generate()
        assert result.returncode == 0, result.stderr
        target = ast.literal_eval((work / 'probe.gypd').read_text())['targets'][0]
        assert target['configurations']['Default']['defines'] == [f'V8_EMBEDDER_STRING="{embedder}-emberbsd.{digest[:16]}"']
    for package, digest in [('lang/v8', 'invalid'), ('lang/nodejs', 'f' * 64)]:
        record.update(package=package, tree_sha256=digest)
        result = generate()
        assert result.returncode and 'invalid prepared source receipt' in result.stderr, result.stderr
print('Node GYP retained its embedder version and keyed V8 caches to the selected tree')
